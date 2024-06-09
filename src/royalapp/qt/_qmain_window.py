from __future__ import annotations

from timeit import default_timer as timer
import logging
from typing import Hashable, TypeVar, TYPE_CHECKING
from pathlib import Path
import app_model
import psygnal
from qtpy import QtWidgets as QtW, QtGui, QtCore
from qtpy.QtCore import Qt
from app_model.backends.qt import QModelMainWindow, QModelMenu
from royalapp.qt._qtab_widget import QTabWidget
from royalapp.qt._qsub_window import QSubWindow, QSubWindowArea
from royalapp.qt._qdock_widget import QDockWidget
from royalapp.types import (
    DockArea,
    DockAreaString,
    WidgetDataModel,
    ClipboardDataModel,
    SubWindowState,
    WindowRect,
)
from royalapp.style import get_style
from royalapp.app import get_event_loop_handler
from royalapp import widgets
from royalapp.qt.registry import pick_widget_class
from royalapp.qt._utils import (
    get_clipboard_data,
    set_clipboard_data,
    ArrayQImage,
    qsignal_blocker,
)

if TYPE_CHECKING:
    from royalapp.widgets._main_window import SubWindow, MainWindow

_STYLE_QSS_PATH = Path(__file__).parent / "style.qss"
_T = TypeVar("_T", bound=QtW.QWidget)
_LOGGER = logging.getLogger(__name__)


class QMainWindow(QModelMainWindow, widgets.BackendMainWindow[QtW.QWidget]):
    _royalapp_main_window: MainWindow

    def __init__(self, app: app_model.Application):
        _app_instance = get_event_loop_handler("qt", app.name)
        self._qt_app = _app_instance.get_app()
        self._app_name = app.name

        app_model_app = widgets.init_application(app)
        super().__init__(app_model_app)
        self._tab_widget = QTabWidget()
        default_menu_ids = {
            "file": "File",
            "window": "Window",
            "tab": "Tab",
            "plugins": "Plugins",
        }
        default_menu_ids.update(
            {
                menu_id: menu_id.replace("_", " ").title()
                for menu_id, _ in app_model_app.menus
                if _is_root_menu_id(app_model_app, menu_id)
            }
        )
        self._menubar = self.setModelMenuBar(default_menu_ids)
        self._toolbar = self.addModelToolBar(menu_id="toolbar")
        self._toolbar.setMovable(False)
        self._toolbar.setFixedHeight(32)
        self.setCentralWidget(self._tab_widget)

        style = get_style("default")
        style_text = (
            _STYLE_QSS_PATH.read_text()
            .replace("$(foreground-1)", style.foreground.level_1)
            .replace("$(foreground-2)", style.foreground.level_2)
            .replace("$(foreground-3)", style.foreground.level_3)
            .replace("$(background-1)", style.background.level_1)
            .replace("$(background-2)", style.background.level_2)
            .replace("$(background-3)", style.background.level_3)
        )
        self.setStyleSheet(style_text)
        self._tab_widget.newWindowActivated.connect(self._update_context)
        self.setMinimumSize(400, 300)

    def add_dock_widget(
        self,
        widget: QtW.QWidget,
        *,
        title: str | None = None,
        area: DockAreaString | DockArea | None = DockArea.RIGHT,
        allowed_areas: list[DockAreaString | DockArea] | None = None,
    ) -> QDockWidget:
        # Normalize title and areas
        if title is None:
            title = widget.objectName()
        if allowed_areas is None:
            allowed_areas = [
                DockArea.LEFT,
                DockArea.RIGHT,
                DockArea.TOP,
                DockArea.BOTTOM,
            ]
        else:
            allowed_areas = [DockArea(area) for area in allowed_areas]
        areas = Qt.DockWidgetArea.NoDockWidgetArea
        for allowed_area in allowed_areas:
            areas |= _DOCK_AREA_MAP[allowed_area]

        # Construct and add the dock widget
        dock_widget = QDockWidget(widget, title)
        dock_widget.setAllowedAreas(areas)
        self.addDockWidget(_DOCK_AREA_MAP[area], dock_widget)

        # add an toggleable action
        for child in self._menubar.actions():
            qmenu = child.menu()
            if isinstance(qmenu, QtW.QMenu) and qmenu.title() == "Window":
                qaction = QtW.QAction(title, qmenu)
                qaction.setCheckable(True)
                qaction.setChecked(True)
                qaction.toggled.connect(
                    _dock_widget_action_toggled_callback(qaction, dock_widget)
                )
                dock_widget.visibilityChanged.connect(
                    _dock_widget_vis_changed_callback(qaction, dock_widget)
                )
                qmenu.addAction(qaction)
                break

        return dock_widget

    def _dock_widget_title(self, widget: QtW.QWidget) -> str:
        if isinstance(dock := widget.parentWidget(), QtW.QDockWidget):
            return dock.windowTitle()
        raise ValueError(f"{widget!r} does not have a dock widget parent.")

    def _set_dock_widget_title(self, widget: QtW.QWidget, title: str) -> None:
        if isinstance(dock := widget.parentWidget(), QtW.QDockWidget):
            return dock.setWindowTitle(title)
        raise ValueError(f"{widget!r} does not have a dock widget parent.")

    def _dock_widget_visible(self, widget: QtW.QWidget) -> bool:
        if isinstance(dock := widget.parentWidget(), QtW.QDockWidget):
            return dock.isVisible()
        raise ValueError(f"{widget!r} does not have a dock widget parent.")

    def _set_dock_widget_visible(self, widget: QtW.QWidget, visible: bool) -> None:
        if isinstance(dock := widget.parentWidget(), QtW.QDockWidget):
            return dock.setVisible(visible)
        raise ValueError(f"{widget!r} does not have a dock widget parent.")

    def add_tab(self, tab_name: str) -> QSubWindowArea:
        """
        Add a new tab with a sub-window area.

        Parameters
        ----------
        tab_name : str
            Name of the tab.
        """
        return self._tab_widget.addTabArea(tab_name)

    def add_widget(
        self,
        widget: _T,
        i_tab: int,
        title: str | None = None,
    ) -> QSubWindow:
        if not isinstance(widget, QtW.QWidget):
            raise TypeError(
                f"`widget` must be a QtW.QWidget instance, got {type(widget)}."
            )
        tab = self._tab_widget.widget(i_tab)
        subwindow = tab.add_widget(widget, title)
        return subwindow

    def _connect_window_events(self, sub: SubWindow, qsub: QSubWindow):
        qsub.state_changed.connect(lambda state: sub.state_changed.emit(state))
        qsub.closed.connect(lambda: sub.closed.emit())

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        super().resizeEvent(event)
        if widget := self._tab_widget.currentWidget():
            widget._reanchor_windows()
        return None

    def showEvent(self, event: QtGui.QShowEvent) -> None:
        super().showEvent(event)
        if widget := self._tab_widget.currentWidget():
            widget._reanchor_windows()
        return None

    def show(self):
        super().show()
        size = self.size()
        minw, minh = 600, 400
        if size.width() < minw or size.height() < minh:
            self.resize(min(size.width(), minw), min(size.height(), minh))
        return None

    def event(self, e: QtCore.QEvent) -> bool:
        if e.type() in {
            QtCore.QEvent.Type.WindowActivate,
            QtCore.QEvent.Type.ZOrderChange,
        }:
            # upon activation or raise_, put window at the end of _instances
            widgets.set_current_instance(self._app_name, self._royalapp_main_window)

        res = super().event(e)

        if e.type() == QtCore.QEvent.Type.Close and e.isAccepted():
            widgets.remove_instance(self._app_name, self._royalapp_main_window)

        return res

    def _update_context(self) -> None:
        _time_0 = timer()
        ctx = self._royalapp_main_window._ctx_keys
        ctx._update(self._royalapp_main_window)
        _dict = ctx.dict()
        self._menubar.update_from_context(_dict)
        _msec = (timer() - _time_0) * 1000
        _LOGGER.info(f"Context update took {_msec:.3f} msec")

    def _run_app(self):
        return get_event_loop_handler("qt", self._app_name).run_app()

    def _current_tab_index(self) -> int:
        return self._tab_widget.currentIndex()

    def _set_current_tab_index(self, i_tab: int) -> None:
        return self._tab_widget.setCurrentIndex(i_tab)

    def _current_sub_window_index(self) -> int:
        area = self._tab_widget.currentWidget()
        if area is None:
            return -1
        sub = area.currentSubWindow()
        if sub is None:
            return -1
        return area.subWindowList().index(sub)

    def _set_current_sub_window_index(self, i_window: int) -> None:
        area = self._tab_widget.currentWidget()
        area.activateWindow(area.subWindowList()[i_window])
        return None

    def _tab_title(self, i_tab: int) -> str:
        return self._tab_widget.tabText(i_tab)

    def _set_tab_title(self, i_tab: int, title: str) -> None:
        return self._tab_widget.setTabText(i_tab, title)

    def _window_title(self, widget: QtW.QWidget) -> str:
        window = widget.parentWidget().parentWidget()
        if not isinstance(window, QSubWindow):
            raise ValueError(f"Widget {widget!r} is not in a sub-window.")
        return window.windowTitle()

    def _set_window_title(self, widget: QtW.QWidget, title: str) -> None:
        window = widget.parentWidget().parentWidget()
        if not isinstance(window, QSubWindow):
            raise ValueError(f"Widget {widget!r} is not in a sub-window.")
        return window.setWindowTitle(title)

    def _pick_widget_class(self, type: Hashable) -> QtW.QWidget:
        return pick_widget_class(self._app_name, type)

    def _provide_file_output(self) -> WidgetDataModel:
        if sub := self._tab_widget.currentWidget().currentSubWindow():
            active_window = sub.main_widget()
            if not hasattr(active_window, "to_model"):
                raise ValueError("Widget does not have `to_model` method.")
            return active_window.to_model()
        else:
            raise ValueError("No active window.")

    def _open_file_dialog(self, mode: str = "r") -> Path | list[Path] | None:
        if mode == "r":
            path = QtW.QFileDialog.getOpenFileName(self, "Open File")[0]
            if path:
                return Path(path)
        elif mode == "w":
            path = QtW.QFileDialog.getSaveFileName(self, "Save File")[0]
            if path:
                return Path(path)
        elif mode == "rm":
            paths = QtW.QFileDialog.getOpenFileNames(self, "Open Files")[0]
            if paths:
                return [Path(p) for p in paths]
        elif mode == "d":
            path = QtW.QFileDialog.getExistingDirectory(self, "Open Directory")
            if path:
                return Path(path)
        return None

    def _open_confirmation_dialog(self, message: str) -> bool:
        answer = QtW.QMessageBox.question(self, "Confirmation", message)
        return answer == QtW.QMessageBox.StandardButton.Yes

    def _exit_main_window(self) -> None:
        self.close()

    def _close_current_window(self) -> None:
        self._tab_widget.removeTab(self._tab_widget.currentIndex())
        return None

    def _get_tab_name_list(self) -> list[str]:
        return [self._tab_widget.tabText(i) for i in range(self._tab_widget.count())]

    def _get_widget_list(self, i_tab: int) -> list[tuple[str, QtW.QWidget]]:
        tab = self._tab_widget.widget(i_tab)
        if tab is None:
            return []
        return [(w.windowTitle(), w.main_widget()) for w in tab.subWindowList()]

    def _del_widget_at(self, i_tab: int, i_window: int) -> None:
        if i_tab < 0 or i_window < 0:
            raise ValueError("Invalid tab or window index.")
        tab = self._tab_widget.widget(i_tab)
        tab.removeSubWindow(tab.subWindowList()[i_window])
        return None

    def _del_tab_at(self, i_tab: int) -> None:
        sub = self._tab_widget.widget(i_tab)
        for window in sub.subWindowList():
            window._close_me()
        self._tab_widget.removeTab(i_tab)
        return None

    def _window_state(self, widget: QtW.QWidget) -> SubWindowState:
        return _get_subwindow(widget).state

    def _set_window_state(self, widget: QtW.QWidget, state: SubWindowState) -> None:
        _get_subwindow(widget).state = state
        return None

    def _window_rect(self, widget: QtW.QWidget) -> WindowRect:
        geo = _get_subwindow(widget).geometry()
        return WindowRect(geo.x(), geo.y(), geo.width(), geo.height())

    def _set_window_rect(self, widget: QtW.QWidget, rect: WindowRect) -> None:
        _get_subwindow(widget).setGeometry(rect.left, rect.top, rect.width, rect.height)
        return None

    def _area_size(self) -> tuple[int, int]:
        size = self._tab_widget.currentWidget().size()
        return size.width(), size.height()

    def _clipboard_data(self) -> ClipboardDataModel | None:
        return get_clipboard_data()

    def _set_clipboard_data(self, data: ClipboardDataModel) -> None:
        return set_clipboard_data(data)

    def _connect_activation_signal(self, sig: psygnal.SignalInstance):
        self._tab_widget.newWindowActivated.connect(sig.emit)

    def _add_model_menu(
        self,
        id_: str,
        title: str | None = None,
    ) -> None:
        if title is None:
            title = id_.title()
        menu = self._menubar
        menu.addMenu(QModelMenu(id_, self._app, title, self))

    def _screenshot(self, target: str):
        if target == "main":
            qimg = self.grab().toImage()
        elif target == "area":
            if widget := self._tab_widget.currentWidget():
                qimg = widget.grab().toImage()
            else:
                raise ValueError("No active area.")
        elif target == "window":
            if sub := self._tab_widget.currentWidget().currentSubWindow():
                qimg = sub.main_widget().grab().toImage()
            else:
                raise ValueError("No active window.")
        return ArrayQImage(qimg)


_DOCK_AREA_MAP = {
    DockArea.TOP: Qt.DockWidgetArea.TopDockWidgetArea,
    DockArea.BOTTOM: Qt.DockWidgetArea.BottomDockWidgetArea,
    DockArea.LEFT: Qt.DockWidgetArea.LeftDockWidgetArea,
    DockArea.RIGHT: Qt.DockWidgetArea.RightDockWidgetArea,
    None: Qt.DockWidgetArea.NoDockWidgetArea,
}


def _is_root_menu_id(app: app_model.Application, menu_id: str) -> bool:
    if menu_id in ("toolbar", app.menus.COMMAND_PALETTE_ID):
        return False
    return "/" not in menu_id.replace("//", "")


def _dock_widget_action_toggled_callback(action: QtW.QAction, dock: QtW.QDockWidget):
    def _cb():
        dock.setVisible(action.isChecked())

    return _cb


def _dock_widget_vis_changed_callback(action: QtW.QAction, dock: QtW.QDockWidget):
    def _cb():
        with qsignal_blocker(dock):
            action.setChecked(dock.isVisible())

    return _cb


def _get_subwindow(widget: QtW.QWidget) -> QSubWindow:
    window = widget.parentWidget().parentWidget()
    if not isinstance(window, QSubWindow):
        raise ValueError(f"Widget {widget!r} is not in a sub-window.")
    return window
