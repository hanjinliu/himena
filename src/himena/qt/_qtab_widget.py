from __future__ import annotations

import sys
from typing import Callable
from app_model import Application
from app_model.types import MenuItem
from qtpy import QtWidgets as QtW, QtCore, QtGui
from qtpy.QtCore import Qt
from superqt.utils import thread_worker
from himena.qt._qclickable_label import QClickableLabel
from himena.qt._qsub_window import QSubWindowArea, QSubWindow
from himena.qt._qrename import QTabRenameLineEdit
from himena.qt._utils import get_main_window
from himena.consts import ActionGroup, MenuId, MonospaceFontFamily
from himena import _drag
from himena.types import WindowRect
from himena.workflow._reader import ReaderMethod


class QCloseTabToolButton(QtW.QToolButton):
    def __init__(self, area: QSubWindowArea):
        super().__init__()
        self._subwindow_area = area
        self.setText("✕")
        self.setFixedSize(12, 12)
        self.clicked.connect(self.close_area)
        self.setToolTip("Close this tab")
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def close_area(self):
        main = get_main_window(self)
        tab_widget = main._backend_main_window._tab_widget
        for i in range(tab_widget.count()):
            if tab_widget.widget_area(i) is self._subwindow_area:
                tab_widget.setCurrentIndex(i)
                main.exec_action("close-tab")


class QTabBar(QtW.QTabBar):
    """Tab bar used for the main widget"""

    def __init__(self, parent: QtW.QTabWidget | None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self._pressed_pos = QtCore.QPoint()

        # "new tab" button
        tb = QtW.QToolButton()
        tb.setParent(parent)
        tb.setText("+")
        tb.setFont(QtGui.QFont(MonospaceFontFamily, 12, 15))
        tb.setToolTip("New Tab")
        tb.clicked.connect(lambda: get_main_window(self).add_tab())
        tb.setFixedWidth(20)
        tb.hide()
        self._plus_btn = tb
        self._plus_btn.setFixedHeight(18)

    def dragEnterEvent(self, e: QtGui.QDragEnterEvent) -> None:
        e.accept()

    def dropEvent(self, e: QtGui.QDropEvent) -> None:
        if isinstance(sub := e.source(), QSubWindow):
            target_index = self.tabAt(e.pos())
            self._process_drop_event(sub, target_index)
        elif model := _drag.drop():
            model = model.data_model()
            main = get_main_window(self)
            main.tabs[target_index].add_data_model(model)
        return super().dropEvent(e)

    def resizeEvent(self, a0):
        super().resizeEvent(a0)
        self._move_plus_btn()

    def tabLayoutChange(self):
        super().tabLayoutChange()
        self._move_plus_btn()

    def showEvent(self, a0):
        super().showEvent(a0)
        self._move_plus_btn()

    def _move_plus_btn(self) -> None:
        """Move the "+" button to the right of the last tab."""
        if self.tab_widget()._is_startup_only():
            self._plus_btn.hide()
            return None
        self._plus_btn.show()
        size = self.width()
        self._plus_btn.move(size + 4, 1)
        self._plus_btn.show()
        return None

    def _process_drop_event(self, sub: QSubWindow, target_index: int) -> None:
        # this is needed to initialize the drag state
        sub._title_bar._drag_position = None
        # move window to the new tab
        i_tab, i_win = sub._find_me()
        main = get_main_window(self)
        main.move_window(main.tabs[i_tab][i_win], target_index)

    def mousePressEvent(self, event: QtGui.QMouseEvent):
        self._pressed_pos = event.pos()
        if event.button() == Qt.MouseButton.LeftButton:
            i_tab = self.tabAt(self._pressed_pos)
            if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                if area := self.tab_widget().widget_area(i_tab):
                    drag = QtGui.QDrag(area)
                    mime_data = QtCore.QMimeData()
                    text = f"himena-tab:{i_tab}"
                    mime_data.setText(text)
                    drag.setMimeData(mime_data)
                    drag.setPixmap(area._pixmap_resized(QtCore.QSize(150, 150)))
                    drag.exec()
        return None

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent):
        i_tab_released = self.tabAt(event.pos())
        i_tab_pressed = self.tabAt(self._pressed_pos)
        if i_tab_released == i_tab_pressed:
            self.setCurrentIndex(i_tab_released)
        return super().mouseReleaseEvent(event)

    def tab_widget(self) -> QTabWidget:
        return self.parentWidget()


class QTabWidget(QtW.QTabWidget):
    """Tab widget used for the main widget"""

    activeWindowChanged = QtCore.Signal(bool)  # True if a window is active
    resized = QtCore.Signal()

    def __init__(self):
        super().__init__()
        self._tabbar = QTabBar(self)
        self.setTabBar(self._tabbar)
        self._line_edit = QTabRenameLineEdit(self)
        self._current_edit_index = None
        self._startup_widget: QStartupWidget | None = None

        self.setTabBarAutoHide(False)
        self.currentChanged.connect(self._on_current_changed)
        self.setSizePolicy(
            QtW.QSizePolicy.Policy.Expanding, QtW.QSizePolicy.Policy.Expanding
        )
        self.setMinimumSize(200, 200)
        self.setAcceptDrops(True)

        self.activeWindowChanged.connect(self._repolish)
        self._tabbar._plus_btn.hide()

    def _init_startup(self):
        self._startup_widget = QStartupWidget(self)
        self._add_startup_widget()

    def add_tab_area(self, tab_name: str | None = None) -> QSubWindowArea:
        """Add a new tab with a sub-window area.

        Parameters
        ----------
        tab_name : str
            Name of the tab.
        """
        if tab_name is None:
            tab_name = "Tab"
        if self._is_startup_only():
            self.removeTab(0)
            self.setTabBarAutoHide(False)
        area = QSubWindowArea()
        self.addTab(area, tab_name)
        area.subWindowActivated.connect(self._subwindow_activated)
        area.area_focused.connect(self._area_focused)
        btn = QCloseTabToolButton(area)
        self.tabBar().setTabButton(
            self.count() - 1, QtW.QTabBar.ButtonPosition.RightSide, btn
        )
        return area

    def remove_tab_area(self, index: int) -> None:
        if self._is_startup_only():
            raise ValueError("No tab in the tab widget.")
        self.removeTab(index)
        if self.count() == 0:
            self._add_startup_widget()
        return None

    def _subwindow_activated(self, win: QSubWindow | None) -> None:
        if win is not None:
            self.activeWindowChanged.emit(True)

    def _area_focused(self) -> None:
        self.activeWindowChanged.emit(False)

    def _add_startup_widget(self):
        self.addTab(self._startup_widget, ".welcome")
        self.setTabBarAutoHide(True)
        self._startup_widget.rebuild()

    def _is_startup_only(self) -> bool:
        return self.count() == 1 and self.widget(0) == self._startup_widget

    def _on_current_changed(self, index: int) -> None:
        if widget := self.widget_area(index):
            has_active_subwindow = any(
                win.is_current() for win in widget.subWindowList()
            )
            self.activeWindowChanged.emit(has_active_subwindow)

    def _repolish(self, subwindow_focused: bool = True) -> None:
        if area := self.current_widget_area():
            wins = area.subWindowList()
            if subwindow_focused:
                cur = area.currentSubWindow()
            else:
                cur = None
            for i, win in enumerate(wins):
                win.set_is_current(win == cur)

    def dragEnterEvent(self, e: QtGui.QDragEnterEvent) -> None:
        # This override is necessary for accepting drops from files.
        if isinstance(e.source(), QSubWindowArea):
            e.ignore()
        else:
            e.accept()

    def dropEvent(self, event: QtGui.QDropEvent) -> None:
        mime_data = event.mimeData()
        glob_pos = QtGui.QCursor.pos()
        if area := self.current_widget_area():
            drop_pos = area.mapFromGlobal(glob_pos)
        else:
            drop_pos = event.pos()

        ui = get_main_window(self)
        if QtW.QApplication.widgetAt(glob_pos) is self:
            # dropped on the tabbar outside the existing tabs
            if isinstance(src := event.source(), QSubWindow):
                self._tabbar._process_drop_event(src, -1)
        elif model := _drag.drop():
            if (
                isinstance(src := event.source(), QSubWindow)
                and src in self.current_widget_area().subWindowList()
            ):
                # subwindow dropped in the same tab
                pass
            else:
                model = model.data_model()
                model.window_rect_override = lambda s: _center_title_bar_on(s, drop_pos)
                ui.add_data_model(model)
        elif mime_data.hasUrls():
            if isinstance(win := event.source(), QSubWindow):
                # subwindow dragged and dropped without changing tabs
                if win in self.current_widget_area().subWindowList():
                    event.ignore()
                return super().dropEvent(event)
            urls = mime_data.urls()
            paths = [url.toLocalFile() for url in urls if url.isLocalFile()]
            future = ui.read_files_async(paths)
            ui._backend_main_window._add_job_progress(future, "Reading files")
            ui.model_app.injection_store.process(future)
        elif callable(rft := getattr(mime_data.parent(), "readers_from_text", None)):
            readers = rft(mime_data.text())
            worker = self._read_one_by_one(readers)
            worker.yielded.connect(ui.add_data_model)
            worker.start()
            ui.set_status_tip("Opening files from remote sources ...", duration=2)
        return super().dropEvent(event)

    def widget_area(self, index: int) -> QSubWindowArea | None:
        """Get the QSubWindowArea widget at index."""
        if self._is_startup_only():
            return None
        return self.widget(index)

    def current_widget_area(self) -> QSubWindowArea | None:
        """Get the current QSubWindowArea widget."""
        if self._is_startup_only():
            return None
        return self.currentWidget()

    def resizeEvent(self, a0):
        super().resizeEvent(a0)
        self.resized.emit()
        self._tabbar.setMaximumWidth(self.width() - 22)
        return None

    @thread_worker
    def _read_one_by_one(self, readers: list[ReaderMethod]):
        for reader in readers:
            model = reader.run()
            yield model


class QStartupWidget(QtW.QWidget):
    """The widget for the startup tab."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        self._app = get_main_window(self).model_app
        self._to_delete: list[QtW.QWidget] = []

        _layout = QtW.QVBoxLayout(self)
        _layout.setContentsMargins(12, 12, 12, 12)
        _layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)

        _group_top = QtW.QGroupBox("Start")
        _layout_top = QtW.QVBoxLayout(_group_top)
        _layout_top.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
        _layout.addWidget(_group_top)

        _widget_bottom = QtW.QWidget()
        _layout_bottom = QtW.QHBoxLayout(_widget_bottom)
        _layout_bottom.setContentsMargins(0, 0, 0, 0)
        _layout.addWidget(_widget_bottom)

        _group_bottom_left = QtW.QGroupBox("Recent Files")
        self._layout_bottom_left = QtW.QVBoxLayout(_group_bottom_left)
        self._layout_bottom_left.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
        _layout_bottom.addWidget(_group_bottom_left)

        _group_bottom_right = QtW.QGroupBox("Recent Sessions")
        self._layout_bottom_right = QtW.QVBoxLayout(_group_bottom_right)
        self._layout_bottom_right.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
        _layout_bottom.addWidget(_group_bottom_right)

        self.setMinimumSize(0, 0)
        # top:bottom = 1:2
        _layout.setStretch(0, 1)
        _layout.setStretch(1, 2)

        self._add_buttons(_layout_top, MenuId.STARTUP)
        return None

    def _make_button(self, command_id: str, app: Application) -> QClickableLabel:
        def callback():
            app.commands.execute_command(command_id)

        cmd = app.commands[command_id]
        if kb := app.keybindings.get_keybinding(command_id):
            kb_text = kb.keybinding.to_text(sys.platform)
            text = f"{cmd.title} ({kb_text})"
        else:
            text = cmd.title
        label = QClickableLabel(text)
        label.clicked.connect(callback)
        return label

    def rebuild(self):
        for btn in self._to_delete:
            btn.deleteLater()
        self._to_delete.clear()

        btns_files = self._add_buttons(
            self._layout_bottom_left, MenuId.FILE_RECENT, self._is_recent_file
        )
        btns_sessions = self._add_buttons(
            self._layout_bottom_right, MenuId.FILE_RECENT, self._is_recent_session
        )
        self._to_delete.extend(btns_files)
        self._to_delete.extend(btns_sessions)

    def _is_recent_file(self, menu: MenuItem) -> bool:
        return menu.group == ActionGroup.RECENT_FILE

    def _is_recent_session(self, menu: MenuItem) -> bool:
        return menu.group == ActionGroup.RECENT_SESSION

    def _add_buttons(
        self,
        layout: QtW.QVBoxLayout,
        menu_id: str,
        filt: Callable[[MenuItem], bool] = lambda x: True,
    ) -> list[QClickableLabel]:
        added: list[QClickableLabel] = []
        for menu in self._app.menus.get_menu(menu_id):
            if isinstance(menu, MenuItem) and filt(menu):
                btn = self._make_button(menu.command.id, self._app)
                layout.addWidget(btn)
                added.append(btn)
        return added


def _center_title_bar_on(size: tuple[int, int], pos: QtCore.QPoint) -> WindowRect:
    width, height = size
    x = pos.x() - width // 2
    y = pos.y() - 6
    return WindowRect(x, y, width, height)
