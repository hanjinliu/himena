from __future__ import annotations
from concurrent.futures import Future
import inspect
from timeit import default_timer as timer
import logging
from typing import Callable, Hashable, Literal, TypeVar, TYPE_CHECKING, cast
from pathlib import Path
import warnings
import weakref
import numpy as np

from qtpy import QtWidgets as QtW, QtGui, QtCore
from app_model.backends.qt import QModelMainWindow, QModelMenu, QMenuItemAction
from superqt import QIconifyIcon
from superqt.utils import ensure_main_thread
from himena.consts import MenuId
from himena.consts import ParametricWidgetProtocolNames as PWPN
from himena.utils.window_rect import prevent_window_overlap
from himena._app_model import _formatter, HimenaApplication
from himena._utils import doc_to_whats_this
from himena.qt._qnotification import QJobStack, QNotificationWidget, QWhatsThisWidget
from himena.qt._qtab_widget import QTabWidget
from himena.qt._qstatusbar import QStatusBar
from himena.qt._qsub_window import QSubWindow, QSubWindowArea, get_subwindow
from himena.qt._qdock_widget import QDockWidget
from himena.qt._qcommand_palette import QCommandPalette
from himena.qt._qcontrolstack import QControlStack
from himena.qt._qparametric import QParametricWidget
from himena.qt._qgoto import QGotoWidget
from himena.qt._qresult_stack import QResultStack
from himena.types import (
    DockArea,
    DockAreaString,
    ClipboardDataModel,
    Size,
    WindowState,
    WindowRect,
    BackendInstructions,
)
from himena.app import get_event_loop_handler
from himena import widgets
from himena.qt.registry import list_widget_class
from himena.qt._utils import get_stylesheet_path, ArrayQImage, ndarray_to_qimage

if TYPE_CHECKING:
    from PyQt6 import QtWidgets as QtW
    from himena.widgets._main_window import SubWindow, MainWindow
    from himena.style import Theme

_ICON_PATH = Path(__file__).parent.parent / "resources" / "icon.svg"
_T = TypeVar("_T", bound=QtW.QWidget)
_V = TypeVar("_V")
_LOGGER = logging.getLogger(__name__)


class QMainWindow(QModelMainWindow, widgets.BackendMainWindow[QtW.QWidget]):
    """The Qt mainwindow implementation for himena."""

    _himena_main_window: MainWindow
    _app: HimenaApplication
    status_tip_requested = QtCore.Signal(str, float)
    notification_requested = QtCore.Signal(str, float)

    def __init__(self, app: HimenaApplication):
        # app must be initialized
        _event_loop_handler = get_event_loop_handler("qt", app.name)
        self._qt_app = cast(QtW.QApplication, _event_loop_handler.get_app())
        self._app_name = app.name
        self._event_loop_handler = _event_loop_handler

        super().__init__(app)
        self._qt_app.setApplicationName(app.name)
        self.setWindowTitle("himena")
        self.setWindowIcon(QtGui.QIcon(_ICON_PATH.as_posix()))
        self._tab_widget = QTabWidget()
        default_menu_ids = {
            MenuId.FILE: MenuId.FILE.capitalize(),
            MenuId.WINDOW: MenuId.WINDOW.capitalize(),
            MenuId.VIEW: MenuId.VIEW.capitalize(),
            MenuId.TOOLS: MenuId.TOOLS.capitalize(),
        }
        default_menu_ids.update(
            {
                menu_id: menu_id.replace("_", " ").title()
                for menu_id, _ in app.menus
                if _is_root_menu_id(app, menu_id)
            }
        )
        # Menubar
        self._menubar = self.setModelMenuBar(default_menu_ids)

        # Toolbar
        self._toolbar = self.addModelToolBar(menu_id=MenuId.TOOLBAR)
        self._toolbar.setContextMenuPolicy(
            QtCore.Qt.ContextMenuPolicy.PreventContextMenu
        )
        self._toolbar.setMovable(False)
        self._toolbar.setFixedHeight(32)
        self._toolbar.addSeparator()
        self._control_stack = QControlStack(self._toolbar)
        self._toolbar.addWidget(self._control_stack)

        self.setCentralWidget(self._tab_widget)

        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)

        self._command_palette_general = QCommandPalette(
            self._app,
            parent=self,
            formatter=_formatter.formatter_general,
        )
        self._command_palette_recent = QCommandPalette(
            self._app,
            menu_id=MenuId.RECENT_ALL,
            parent=self,
            exclude=["open-recent"],
            formatter=_formatter.formatter_recent,
            placeholder="Open recent file ...",
        )
        self._command_palette_new = QCommandPalette(
            self._app,
            menu_id=MenuId.FILE_NEW,
            parent=self,
            exclude=["new"],
            formatter=_formatter.formatter_general,
            placeholder="New ...",
        )
        self._goto_widget = QGotoWidget(self)

        self._anim_subwindow = QtCore.QPropertyAnimation()
        self._confirm_close = True
        self.setMinimumSize(400, 300)
        self.resize(1000, 720)

        # connect notifications
        self._event_loop_handler.errored.connect(self._on_error)
        self._event_loop_handler.warned.connect(self._on_warning)
        self.status_tip_requested.connect(self._on_status_tip_requested)
        self.notification_requested.connect(self._on_show_notification_requested)

        # job stack
        self._job_stack = QJobStack(self)
        self._job_stack.setAnchor("bottom_left")

    def _update_widget_theme(self, style: Theme):
        self.setStyleSheet(style.format_text(get_stylesheet_path().read_text()))
        if style.is_light_background():
            icon_color = "#333333"
        else:
            icon_color = "#CCCCCC"
        for action in self._toolbar.actions():
            if isinstance(action, QMenuItemAction):
                btn = self._toolbar.widgetForAction(action)
                icon = self._app._registered_actions[action._command_id].icon
                if icon is not None:
                    qicon = QIconifyIcon(icon.light, color=icon_color)
                    btn.setIcon(qicon)
                    btn.actions()[0].setIcon(qicon)
        for i in range(self._tab_widget.count()):
            if area := self._tab_widget.widget_area(i):
                for sub in area.subWindowList():
                    sub._title_bar._set_icon_color(icon_color)

    def _main_window_rect(self) -> WindowRect:
        geo = self.geometry()
        return WindowRect(geo.x(), geo.y(), geo.width(), geo.height())

    def _set_main_window_rect(self, rect: WindowRect) -> None:
        self.setGeometry(rect.left, rect.top, rect.width, rect.height)
        return None

    @ensure_main_thread
    def _on_error(self, exc: Exception) -> None:
        from himena.qt._qtraceback import QtErrorMessageBox

        mbox = QtErrorMessageBox.from_exc(exc, parent=self)
        notification = QNotificationWidget(self)
        notification.addWidget(mbox)
        return notification.show_and_hide_later()

    @ensure_main_thread
    def _on_warning(self, warning: warnings.WarningMessage) -> None:
        from himena.qt._qtraceback import QtErrorMessageBox

        mbox = QtErrorMessageBox.from_warning(warning, parent=self)
        notification = QNotificationWidget(self)
        notification.addWidget(mbox)
        return notification.show_and_hide_later()

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
        # Construct and add the dock widget
        dock_widget = QDockWidget(widget, title, allowed_areas)
        self.addDockWidget(dock_widget.area_normed(area), dock_widget)
        dock_widget.closed.connect(self._update_context)
        if doc := getattr(widget, "__doc__", ""):
            dock_widget.whats_this.connect(lambda: self._show_dock_whats_this(doc))
        QtW.QApplication.processEvents()
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

    def _set_control_widget(self, widget: QtW.QWidget, control: QtW.QWidget) -> None:
        if not isinstance(control, QtW.QWidget):
            raise TypeError(
                f"`control_widget` did not return a QWidget (got {type(control)})."
            )
        self._control_stack.add_control_widget(widget, control)

    def _update_control_widget(self, current: QtW.QWidget) -> None:
        self._control_stack.update_control_widget(current)

    def _remove_control_widget(self, widget: QtW.QWidget) -> None:
        self._control_stack.remove_control_widget(widget)

    def _del_dock_widget(self, widget: QtW.QWidget) -> None:
        if isinstance(dock := widget.parentWidget(), QtW.QDockWidget):
            dock.close()
            return None

    def add_tab(self, tab_name: str) -> QSubWindowArea:
        """
        Add a new tab with a sub-window area.

        Parameters
        ----------
        tab_name : str
            Name of the tab.
        """
        _LOGGER.info("Adding tab of title %r", tab_name)
        return self._tab_widget.add_tab_area(tab_name)

    def add_widget(
        self,
        widget: _T,
        i_tab: int,
        title: str,
    ) -> QSubWindow:
        if not isinstance(widget, QtW.QWidget):
            raise TypeError(
                f"Expected a QWidget, got {type(widget)}. If you are adding a wrapper "
                "of a widget, the wrapper should implement `native_widget()` method "
                "that returns QWidget."
            )
        tab = self._tab_widget.widget_area(i_tab)
        _LOGGER.info("Adding widget of title %r to tab %r", title, i_tab)
        subwindow = tab.add_widget(widget, title)
        if self._himena_main_window.theme.is_light_background():
            icon_color = "#333333"
        else:
            icon_color = "#CCCCCC"
        subwindow._set_icon_color(icon_color)
        return subwindow

    def set_widget_as_preview(self, subwindow: SubWindow):
        qsubwindow = get_subwindow(subwindow._split_interface_and_frontend()[1])
        qsubwindow._title_bar._model_menu_btn.hide()
        qsubwindow._title_bar._window_menu_btn.hide()
        return None

    def _connect_window_events(self, sub: SubWindow, qsub: QSubWindow):
        @qsub.state_change_requested.connect
        def _(state: WindowState):
            sub._set_state(state)

        @qsub.close_requested.connect
        def _():
            main = self._himena_main_window
            sub._close_me(main, main._instructions.confirm)

        @qsub.rename_requested.connect
        def _(title: str):
            sub.title = title

    def showEvent(self, event: QtGui.QShowEvent) -> None:
        super().showEvent(event)
        self._himena_main_window._main_window_resized(Size(*self._area_size()))
        return None

    def show(self, run: bool = False):
        super().show()
        size = self.size()
        minw, minh = 600, 400
        if size.width() < minw or size.height() < minh:
            self.resize(min(size.width(), minw), min(size.height(), minh))
        if run:
            get_event_loop_handler("qt", self._app_name).run_app()
        return None

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        if event.spontaneous() and self._confirm_close and not self._ok_to_exit():
            event.ignore()
            return
        return super().closeEvent(event)

    def event(self, e: QtCore.QEvent) -> bool:
        if e.type() in {
            QtCore.QEvent.Type.WindowActivate,
            QtCore.QEvent.Type.ZOrderChange,
        }:
            # upon activation or raise_, put window at the end of _instances
            widgets.set_current_instance(self._app_name, self._himena_main_window)

        res = super().event(e)

        if e.type() == QtCore.QEvent.Type.Close and e.isAccepted():
            widgets.remove_instance(self._app_name, self._himena_main_window)

        return res

    def _ok_to_exit(self) -> bool:
        ui = self._himena_main_window
        if any(win._need_ask_save_before_close() for win in ui.iter_windows()):
            res = ui.exec_choose_one_dialog(
                title="Closing",
                message="There are unsaved changes. Exit anyway?",
                choices=["Exit", "Cancel"],
            )
            return res == "Exit"
        return True

    def _update_context(self) -> None:
        _time_0 = timer()
        ctx = self._himena_main_window._ctx_keys
        ctx._update(self._himena_main_window)
        _dict = ctx.dict()
        self._menubar.update_from_context(_dict)
        _msec = (timer() - _time_0) * 1000
        _LOGGER.debug("Context update took %.3f msec", _msec)

    def _current_tab_index(self) -> int | None:
        idx = self._tab_widget.currentIndex()
        if idx < 0:
            return None
        return idx

    def _set_current_tab_index(self, i_tab: int) -> None:
        return self._tab_widget.setCurrentIndex(i_tab)

    def _tab_hash(self, i_tab: int) -> Hashable:
        return self._tab_widget.widget_area(i_tab)

    def _tab_hash_for_window(self, widget: QtW.QWidget) -> Hashable:
        mdiarea = get_subwindow(widget)._qt_mdiarea()
        assert isinstance(mdiarea, QSubWindowArea)
        return mdiarea

    def _num_tabs(self) -> int:
        if self._tab_widget._is_startup_only():
            return 0
        return self._tab_widget.count()

    def _current_sub_window_index(self, i_tab: int) -> int | None:
        area = self._tab_widget.widget_area(i_tab)
        if area is None:
            return None
        sub = area.currentSubWindow()
        if sub is None or not sub.is_current():
            return None
        return area.subWindowList().index(sub)

    def _set_current_sub_window_index(self, i_tab: int, i_window: int) -> None:
        assert i_window is None or i_window >= 0
        area = self._tab_widget.widget_area(i_tab)
        subwindows = area.subWindowList()
        for i in range(len(subwindows)):
            subwindows[i].set_is_current(i == i_window)
        if i_window is not None:
            area.setActiveSubWindow(subwindows[i_window])
        return None

    def _tab_title(self, i_tab: int) -> str:
        return self._tab_widget.tabText(i_tab)

    def _set_tab_title(self, i_tab: int, title: str) -> None:
        return self._tab_widget.setTabText(i_tab, title)

    def _window_title(self, widget: QtW.QWidget) -> str:
        window = get_subwindow(widget)
        return window.windowTitle()

    def _set_window_title(self, widget: QtW.QWidget, title: str) -> None:
        window = get_subwindow(widget)
        return window.setWindowTitle(title)

    def _list_widget_class(self, type: str):
        return list_widget_class(self._app_name, type)

    def _open_file_dialog(
        self,
        mode: str = "r",
        extension_default: str | None = None,
        allowed_extensions: list[str] | None = None,
        caption: str | None = None,
        start_path: Path | None = None,
    ) -> Path | list[Path] | None:
        if allowed_extensions:
            filter_str = (
                ";".join(_ext_to_filter(ext) for ext in allowed_extensions)
                + ";;All Files (*)"
            )
        else:
            filter_str = "All Files (*)"

        if mode == "r":
            path, _ = QtW.QFileDialog.getOpenFileName(
                self,
                caption=caption or "Open File",
                directory=start_path.as_posix() if start_path else None,
                filter=filter_str,
            )
            if path:
                return Path(path)
        elif mode == "w":
            path, _ = QtW.QFileDialog.getSaveFileName(
                self,
                caption=caption or "Save File",
                directory=start_path.as_posix() if start_path else None,
                filter=filter_str,
            )
            if path:
                output_path = Path(path)
                if output_path.suffix == "" and extension_default is not None:
                    output_path = output_path.with_suffix(extension_default)
                return output_path
        elif mode == "rm":
            paths, _ = QtW.QFileDialog.getOpenFileNames(
                self,
                caption=caption or "Open Files",
                directory=start_path.as_posix() if start_path else None,
                filter=filter_str,
            )
            if paths:
                return [Path(p) for p in paths]
        elif mode == "d":
            path = QtW.QFileDialog.getExistingDirectory(
                self,
                caption=caption or "Open Directory",
                directory=start_path.as_posix() if start_path else None,
            )
            if path:
                return Path(path)
        else:
            raise ValueError(f"Invalid file mode {mode!r}.")
        return None

    def _request_choice_dialog(
        self,
        title: str,
        message: str,
        choices: list[tuple[str, _V]],
        how: Literal["buttons", "radiobuttons"] = "buttons",
    ) -> _V | None:
        if how == "buttons":
            return QChoicesDialog.request(title, message, choices, parent=self)
        else:
            return QChoicesDialog.request_radiobuttons(
                title, message, choices, parent=self
            )

    def _show_command_palette(
        self,
        kind: Literal["general", "recent", "goto", "new"],
    ) -> None:
        if kind == "general":
            self._command_palette_general.update_context(self)
            self._command_palette_general.show()
        elif kind == "recent":
            self._command_palette_general.update_context(self)
            self._command_palette_recent.show()
        elif kind == "goto":
            self._goto_widget.show()
        elif kind == "new":
            self._command_palette_new.update_context(self)
            self._command_palette_new.show()
        else:
            raise NotImplementedError

    def _exit_main_window(self, confirm: bool = False) -> None:
        if confirm and not self._ok_to_exit():
            return None
        return self.close()

    def _get_tab_name_list(self) -> list[str]:
        if self._tab_widget._is_startup_only():
            return []
        return [self._tab_widget.tabText(i) for i in range(self._tab_widget.count())]

    def _get_widget_list(self, i_tab: int) -> list[tuple[str, QtW.QWidget]]:
        tab = self._tab_widget.widget_area(i_tab)
        if tab is None:
            return []
        return [(w.windowTitle(), w._widget) for w in tab.subWindowList()]

    def _del_widget_at(self, i_tab: int, i_window: int) -> None:
        if i_tab < 0 or i_window < 0:
            raise ValueError("Invalid tab or window index.")
        _LOGGER.info("Deleting widget at tab %r, window %r", i_tab, i_window)
        tab = self._tab_widget.widget_area(i_tab)
        subwindows = tab.subWindowList()
        subwindow = subwindows[i_window]
        tab.removeSubWindow(subwindow)
        subwindow._widget._himena_widget = None
        tab.relabel_widgets()
        if len(subwindows) == 1:  # now empty
            tab._set_area_focused()
        return None

    def _del_tab_at(self, i_tab: int) -> None:
        _LOGGER.info("Deleting tab at index %r", i_tab)
        self._tab_widget.remove_tab_area(i_tab)
        return None

    def _rename_window_at(self, i_tab: int, i_window: int) -> None:
        tab = self._tab_widget.widget_area(i_tab)
        window = tab.subWindowList()[i_window]
        window._title_bar._start_renaming()
        return None

    def _window_state(self, widget: QtW.QWidget) -> WindowState:
        return get_subwindow(widget).state

    def _set_window_state(
        self,
        widget: QtW.QWidget,
        state: WindowState,
        inst: BackendInstructions,
    ) -> None:
        get_subwindow(widget)._update_window_state(state, animate=inst.animate)
        return None

    def _window_rect(self, widget: QtW.QWidget) -> WindowRect:
        geo = get_subwindow(widget).geometry()
        return WindowRect(geo.x(), geo.y(), geo.width(), geo.height())

    def _set_window_rect(
        self,
        widget: QtW.QWidget,
        rect: WindowRect,
        inst: BackendInstructions,
    ) -> None:
        qrect = QtCore.QRect(rect.left, rect.top, rect.width, rect.height)
        if inst.animate:
            get_subwindow(widget)._set_geometry_animated(qrect)
        else:
            get_subwindow(widget).setGeometry(qrect)
        return None

    def _area_size(self) -> tuple[int, int]:
        if widget := self._tab_widget.currentWidget():
            size = widget.size()
        else:
            size = self._tab_widget.children()[0].size()
        return size.width(), size.height()

    def _clipboard_data(self) -> ClipboardDataModel | None:
        clipboard = QtGui.QGuiApplication.clipboard()
        if clipboard is None:
            return None
        md = clipboard.mimeData()
        model = ClipboardDataModel()
        if md is None:
            return None
        if md.hasHtml():
            model.html = md.html()
        if md.hasImage():
            model.image = ArrayQImage(clipboard.image())
        if md.hasText():
            model.text = md.text()
        if md.hasUrls():
            model.files = [Path(url.toLocalFile()) for url in md.urls()]
        return model

    def _set_clipboard_data(self, data: ClipboardDataModel) -> None:
        clipboard = QtW.QApplication.clipboard()
        if clipboard is None:
            return
        mime = QtCore.QMimeData()
        if (html := data.html) is not None:
            mime.setHtml(html)
        if (text := data.text) is not None:
            mime.setText(text)
        if (img := data.image) is not None:
            if not isinstance(img, ArrayQImage):
                qimg = ndarray_to_qimage(np.asarray(img, dtype=np.uint8))
            else:
                qimg = img.qimage
            mime.setImageData(qimg)
        if (files := data.files) is not None:
            mime.setUrls([QtCore.QUrl.fromLocalFile(str(f)) for f in files])
        return clipboard.setMimeData(mime)

    def _connect_main_window_signals(self, main: MainWindow):
        self._tab_widget.currentChanged.connect(main._tab_activated)
        self._tab_widget.activeWindowChanged.connect(main._window_activated)
        self._tab_widget.resized.connect(self._emit_resized)

    def _emit_resized(self):
        self._himena_main_window._main_window_resized(Size(*self._area_size()))

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
            qwidget = self
        elif target == "area":
            if widget := self._tab_widget.current_widget_area():
                qwidget = widget
            else:
                raise ValueError("No active area.")
        elif target == "window":
            if sub := self._tab_widget.current_widget_area().currentSubWindow():
                qwidget = sub._widget
            else:
                raise ValueError("No active window.")
        else:
            raise ValueError(f"Invalid target name {target!r}.")
        return ArrayQImage.from_qwidget(qwidget)

    def _process_parametric_widget(
        self,
        widget: QtW.QWidget,
    ) -> QtW.QWidget:
        return QParametricWidget(widget)

    def _connect_parametric_widget_events(
        self,
        wrapper: widgets.ParametricWindow[QParametricWidget],
        widget: QParametricWidget,
    ) -> None:
        widget._call_btn.clicked.connect(wrapper._emit_btn_clicked)
        widget.param_changed.connect(wrapper._emit_param_changed)

    def _signature_to_widget(
        self,
        sig: inspect.Signature,
        show_parameter_labels: bool = True,
        preview: bool = False,
    ) -> QtW.QWidget:
        from magicgui.signature import MagicSignature
        from himena.qt.magicgui import ToggleSwitch, get_type_map

        container = MagicSignature.from_signature(sig).to_container(
            type_map=get_type_map(),
            labels=show_parameter_labels,
        )
        container.margins = (0, 0, 0, 0)
        setattr(container, PWPN.GET_PARAMS, container.asdict)
        setattr(container, PWPN.CONNECT_CHANGED_SIGNAL, container.changed.connect)
        if preview:
            checkbox = ToggleSwitch(value=False, text="Preview")
            container.append(checkbox)
            setattr(container, PWPN.IS_PREVIEW_ENABLED, checkbox.get_value)
        return container

    def _add_widget_to_parametric_window(
        self,
        wrapper: widgets.ParametricWindow[QParametricWidget],
        widget: QtW.QWidget,
        result_as: Literal["below", "right"],
    ):
        if result_as == "below":
            wrapper.widget.add_widget_below(widget)
        elif result_as == "right":
            wrapper.widget.add_widget_right(widget)
        else:
            raise ValueError(f"Invalid result_as value {result_as!r}.")
        if wrapper.is_preview_enabled() and not wrapper._auto_close:
            wrapper.widget._call_btn.hide()

    def _remove_widget_from_parametric_window(
        self,
        wrapper: widgets.ParametricWindow[QParametricWidget],
    ):
        wrapper.widget.remove_result_widget()

    def _move_focus_to(self, win: QtW.QWidget) -> None:
        win.setFocus()
        return None

    def _set_status_tip(self, tip: str, duration: float) -> None:
        self.status_tip_requested.emit(tip, duration)

    def _show_notification(self, text: str, duration: float) -> None:
        self.notification_requested.emit(text, duration)

    def _on_status_tip_requested(self, tip: str, duration: float) -> None:
        return self._status_bar.showMessage(tip, int(duration * 1000))

    def _on_show_notification_requested(self, text: str, duration: float) -> None:
        text_edit = QtW.QPlainTextEdit(text)
        text_edit.setWordWrapMode(QtGui.QTextOption.WrapMode.WordWrap)
        notification = QNotificationWidget(self, duration=int(duration * 1000))
        notification.addWidget(text_edit)
        return notification.show_and_hide_later()

    def _get_menu_action_by_id(self, name: str) -> QtW.QAction:
        # Find the help menu
        for action in self._menubar.actions():
            if isinstance(menu := action.menu(), QModelMenu):
                if menu._menu_id == name:
                    action = action
                    break
        else:
            raise RuntimeError(f"{name} menu not found.")
        return action

    def _rebuild_for_runtime(self, added_menus: list[str]) -> None:
        # Find the help menu
        help_menu_action = self._get_menu_action_by_id("help")

        # insert the new menus to the menubar before the help menu
        for menu_id in added_menus:
            menu = QModelMenu(menu_id, self._app, menu_id.title(), self._menubar)
            self._menubar.insertMenu(help_menu_action, menu)
        # rebuild the menus
        for action in self._menubar.actions():
            if isinstance(menu := action.menu(), QModelMenu):
                menu.rebuild()
        return None

    def _process_future_done_callback(
        self,
        cb: Callable[[Future], None],
        cb_errored: Callable[[Exception], None],
        **kwargs,
    ) -> Callable[[Future], None]:
        def _func(future: Future):
            if future.cancelled():
                self._show_notification("Cancelled.", duration=2)
            elif e := future.exception():
                self._on_error(e)
                cb_errored(e)
            else:
                cb(future, **kwargs)

        return ensure_main_thread(_func)

    def _set_parametric_widget_busy(
        self,
        wrapper: widgets.ParametricWindow[QParametricWidget],
        busy: bool,
    ):
        """Set the parametric widget busy status."""
        wrapper.widget.set_busy(busy)

    def _add_job_progress(self, future: Future, desc: str, total: int = 0) -> None:
        self._job_stack.add_future(future, desc, total)
        return None

    def _add_whats_this(
        self,
        text: str,
        style: Literal["plain", "markdown", "html"] = "plain",
    ) -> None:
        whatsthis = QWhatsThisWidget(self)
        whatsthis.set_text(text, style)
        whatsthis.show()
        return None

    def _show_dock_whats_this(self, doc: str):
        doc_formatted = doc_to_whats_this(doc)
        self._add_whats_this(doc_formatted, style="markdown")

    @ensure_main_thread
    def _append_result(self, item):
        ui = self._himena_main_window
        tab = ui.tabs.current()
        if tab is None:
            tab = ui.add_tab()
        if (result_stack := tab._result_stack_ref()) is None:
            result_stack = QResultStack()
            tab._result_stack_ref = weakref.ref(result_stack)
            sub = tab.current()
            win = tab.add_widget(result_stack, title="Results")
            win.closed.connect(tab._discard_result_stack_ref)
            if sub:
                win.rect = prevent_window_overlap(sub, win, self._area_size())
        result_stack.append_result(item)


def _is_root_menu_id(app: HimenaApplication, menu_id: str) -> bool:
    if menu_id in (MenuId.TOOLBAR, app.menus.COMMAND_PALETTE_ID):
        return False
    return "/" not in menu_id.replace("//", "")


def _ext_to_filter(ext: str) -> str:
    if ext.startswith("."):
        return f"*{ext}"
    elif ext == "":
        return "*"
    else:
        return f"*.{ext}"


class QChoicesDialog(QtW.QDialog):
    def __init__(self, parent: QtW.QWidget | None = None):
        super().__init__(parent)
        self._result = None
        self.accepted.connect(self.close)
        self._layout = QtW.QVBoxLayout(self)
        self._layout.setSpacing(10)

    def set_result_callback(self, value: _V, accept: bool) -> None:
        def _set_result():
            self._result = value
            if accept:
                return self.accept()

        return _set_result

    @classmethod
    def request(
        cls,
        title: str,
        message: str,
        choices: list[tuple[str, _V]],
        parent: QtW.QWidget | None = None,
    ) -> _V | None:
        self = cls(parent)
        self.init_message(title, message)
        button_group = QtW.QDialogButtonBox(self)
        shortcut_registered = set()
        for choice, value in choices:
            button = QtW.QPushButton(choice)
            button_group.addButton(button, button_group.ButtonRole.AcceptRole)
            button.clicked.connect(self.set_result_callback(value, accept=True))
            shortcut = choice[0].lower()
            if shortcut not in shortcut_registered:
                button.setShortcut(shortcut)
                shortcut_registered.add(shortcut)
        self._layout.addWidget(button_group)
        if self.exec() == QtW.QDialog.DialogCode.Accepted:
            return self._result
        return None

    @classmethod
    def request_radiobuttons(
        cls,
        title: str,
        message: str,
        choices: list[tuple[str, _V]],
        parent: QtW.QWidget | None = None,
    ) -> _V | None:
        self = cls(parent)
        self.init_message(title, message)
        button_group = QtW.QButtonGroup(self)
        button_group.setExclusive(True)
        for choice, value in choices:
            button = QtW.QRadioButton(choice)
            button_group.addButton(button)
            button.clicked.connect(self.set_result_callback(value, accept=False))
            self._layout.addWidget(button)
            button.setChecked(choice == choices[0][0])

        ok_cancel = QtW.QDialogButtonBox()
        ok_cancel.addButton(QtW.QDialogButtonBox.StandardButton.Ok)
        ok_cancel.addButton(QtW.QDialogButtonBox.StandardButton.Cancel)
        ok_cancel.accepted.connect(self.accept)
        ok_cancel.rejected.connect(self.reject)
        self._layout.addWidget(ok_cancel)
        if self.exec() == QtW.QDialog.DialogCode.Accepted:
            return self._result
        return None

    def init_message(self, title: str, message: str) -> None:
        self.setWindowTitle(title)
        label = QtW.QLabel(message)
        self._layout.addWidget(label)
        return None
