from __future__ import annotations

from typing import Hashable, TypeVar
from pathlib import Path
from qtpy import QtWidgets as QtW, QtGui, QtCore
from qtpy.QtCore import Qt
from app_model.backends.qt import QModelMainWindow
from royalapp.qt._qtab_widget import QTabWidget
from royalapp.qt._qsub_window import QSubWindow, QSubWindowArea
from royalapp.qt._qdock_widget import QDockWidget
from royalapp.types import (
    DockArea,
    DockAreaString,
    TabTitle,
    WindowTitle,
    WidgetDataModel,
)
from royalapp.style import get_style
from royalapp.app import get_app
from royalapp import widgets
from royalapp.qt._widget_registry import pick_widget_class

_STYLE_QSS_PATH = Path(__file__).parent / "style.qss"
_T = TypeVar("_T", bound=QtW.QWidget)


class QMainWindow(QModelMainWindow, widgets.BackendMainWindow[QtW.QWidget]):
    def __init__(
        self,
        app: str = "royalapp",
    ):
        _app = get_app("qt")
        self._qt_app = _app.get_app()
        self._app_name = app

        app_model_app = widgets.get_application(app)
        super().__init__(app_model_app)
        self._tab_widget = QTabWidget()
        self._menubar = self.setModelMenuBar(menu_ids={"file": "File", "edit": "Edit"})
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

    def add_dock_widget(
        self,
        widget: QtW.QWidget,
        *,
        title: str | None = None,
        area: DockAreaString | DockArea | None = DockArea.RIGHT,
        allowed_areas: list[DockAreaString | DockArea] | None = None,
    ) -> QDockWidget:
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
        dock_widget = QDockWidget(widget, title)
        areas = Qt.DockWidgetArea.NoDockWidgetArea
        for allowed_area in allowed_areas:
            areas |= _DOCK_AREA_MAP[allowed_area]
        dock_widget.setAllowedAreas(areas)
        self.addDockWidget(_DOCK_AREA_MAP[area], dock_widget)
        return dock_widget

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
    ) -> QSubWindow[_T]:
        if not isinstance(widget, QtW.QWidget):
            raise TypeError(
                f"`widget` must be a QtW.QWidget instance, got {type(widget)}."
            )
        size = widget.size()
        sub_window = QSubWindow(widget, title)
        sub_window.resize(size)
        tab = self._tab_widget.widget(i_tab)
        nwindows = len(tab.subWindowList())
        tab.addSubWindow(sub_window)
        sub_window.move(4 + 24 * (nwindows % 5), 4 + 24 * (nwindows % 5))
        return sub_window

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

    def _run_app(self):
        return get_app("qt").run_app()

    def _current_tab_index(self) -> int:
        return self._tab_widget.currentIndex()

    def _set_current_tab_index(self, i_tab: int) -> None:
        return self._tab_widget.setCurrentIndex(i_tab)

    def _current_sub_window_index(self) -> int:
        area = self._tab_widget.currentWidget()
        return area.subWindowList().index(area.currentSubWindow())

    def _set_current_sub_window_index(self, i_window: int) -> None:
        area = self._tab_widget.currentWidget()
        area.activateWindow(area.subWindowList()[i_window])
        return None

    def _set_tab_title(self, i_tab: int, title: TabTitle) -> None:
        return self._tab_widget.setTabText(i_tab, title)

    def _window_title(self, widget: QtW.QWidget) -> WindowTitle:
        window = widget.parentWidget().parentWidget()
        if not isinstance(window, QSubWindow):
            raise ValueError(f"Widget {widget!r} is not in a sub-window.")
        return window.windowTitle()

    def _set_window_title(self, widget: QtW.QWidget, title: WindowTitle) -> None:
        window = widget.parentWidget().parentWidget()
        if not isinstance(window, QSubWindow):
            raise ValueError(f"Widget {widget!r} is not in a sub-window.")
        return window.setWindowTitle(title)

    def _pick_widget_class(self, type: Hashable) -> QtW.QWidget:
        return pick_widget_class(type)

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

    def _get_tab_name_list(self) -> list[TabTitle]:
        return [self._tab_widget.tabText(i) for i in range(self._tab_widget.count())]

    def _get_widget_list(self, i_tab: int) -> list[tuple[str, QtW.QWidget]]:
        tab = self._tab_widget.widget(i_tab)
        return [(w.windowTitle(), w.main_widget()) for w in tab.subWindowList()]

    def _del_widget_at(self, i_tab: int, i_window: int) -> None:
        tab = self._tab_widget.widget(i_tab)
        tab.removeSubWindow(tab.subWindowList()[i_window])
        return None


_DOCK_AREA_MAP = {
    DockArea.TOP: Qt.DockWidgetArea.TopDockWidgetArea,
    DockArea.BOTTOM: Qt.DockWidgetArea.BottomDockWidgetArea,
    DockArea.LEFT: Qt.DockWidgetArea.LeftDockWidgetArea,
    DockArea.RIGHT: Qt.DockWidgetArea.RightDockWidgetArea,
    None: Qt.DockWidgetArea.NoDockWidgetArea,
}
