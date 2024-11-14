from __future__ import annotations

import sys
from qtpy import QtWidgets as QtW, QtCore, QtGui
from qtpy.QtCore import Qt
from himena.qt._qclickable_label import QClickableLabel
from himena.qt._qsub_window import QSubWindowArea, QSubWindow
from himena.qt._qrename import QRenameLineEdit
from himena.qt._utils import get_main_window, build_qmodel_menu


class QCloseTabToolButton(QtW.QToolButton):
    def __init__(self, area: QSubWindowArea):
        super().__init__()
        self._subwindow_area = area
        self.setText("✕")
        self.setFixedSize(12, 12)
        self.clicked.connect(self.close_area)
        self.setToolTip("Close this tab")

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

    def dragEnterEvent(self, e: QtGui.QDragEnterEvent) -> None:
        e.accept()

    def dropEvent(self, e: QtGui.QDropEvent) -> None:
        if isinstance(sub := e.source(), QSubWindow):
            target_index = self.tabAt(e.pos())
            self._process_drop_event(sub, target_index)
        return super().dropEvent(e)

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
            if event.button() == Qt.MouseButton.RightButton:
                build_qmodel_menu
        return super().mouseReleaseEvent(event)

    def tab_widget(self) -> QTabWidget:
        return self.parentWidget()


class QTabWidget(QtW.QTabWidget):
    """Tab widget used for the main widget"""

    newWindowActivated = QtCore.Signal()

    def __init__(self):
        super().__init__()
        self._tabbar = QTabBar(self)
        self.setTabBar(self._tabbar)
        self._line_edit = QRenameLineEdit(self)
        self._current_edit_index = None
        self._startup_widget: QStartupWidget | None = None

        @self._line_edit.rename_requested.connect
        def _(new_name: str):
            if self._current_edit_index is not None:
                self.setTabText(self._current_edit_index, new_name)

        self.setTabBarAutoHide(False)
        self.currentChanged.connect(self._on_current_changed)
        self.tabBarDoubleClicked.connect(self._start_editing_tab)
        self.setSizePolicy(
            QtW.QSizePolicy.Policy.Expanding, QtW.QSizePolicy.Policy.Expanding
        )
        self.setMinimumSize(200, 200)
        self.setAcceptDrops(True)

        self.newWindowActivated.connect(self._repolish)
        self.currentChanged.connect(self._repolish)

        # "new tab" button
        tb = QtW.QToolButton()
        tb.setText("+")
        tb.setFont(QtGui.QFont("Arial", 12, weight=15))
        tb.setToolTip("New Tab")
        tb.clicked.connect(lambda: get_main_window(self).add_tab())
        self.setCornerWidget(tb)

    def _init_startup(self):
        self._startup_widget = QStartupWidget(self)
        self._add_startup_widget()

    def add_tab_area(self, tab_name: str | None = None) -> QSubWindowArea:
        """
        Add a new tab with a sub-window area.

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
        area.subWindowActivated.connect(self._emit_new_window_activated)
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

    def _emit_new_window_activated(self) -> None:
        self.newWindowActivated.emit()

    def _add_startup_widget(self):
        self.addTab(self._startup_widget, ".welcome")
        self.setTabBarAutoHide(True)

    def _is_startup_only(self) -> bool:
        return self.count() == 1 and self.widget(0) == self._startup_widget

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        self._line_edit.setHidden(True)
        return super().mousePressEvent(event)

    def _on_current_changed(self, index: int) -> None:
        if widget := self.widget_area(index):
            widget._reanchor_windows()
            if len(widget.subWindowList()) > 0:
                self.newWindowActivated.emit()
            self._line_edit.setHidden(True)

    def _repolish(self) -> None:
        if area := self.current_widget_area():
            wins = area.subWindowList()
            cur = area.currentSubWindow()
            for i, win in enumerate(wins):
                win.set_is_current(win == cur)

    def _tab_rect(self, index: int) -> QtCore.QRect:
        """Get QRect of the tab at index."""
        rect = self.tabBar().tabRect(index)

        # NOTE: East/South tab returns wrong value (Bug in Qt?)
        if self.tabPosition() == QtW.QTabWidget.TabPosition.East:
            w = self.rect().width() - rect.width()
            rect.translate(w, 0)
        elif self.tabPosition() == QtW.QTabWidget.TabPosition.South:
            h = self.rect().height() - rect.height()
            rect.translate(0, h)

        return rect

    def _move_line_edit(
        self,
        rect: QtCore.QRect,
        text: str,
    ) -> QtW.QLineEdit:
        geometry = self._line_edit.geometry()
        geometry.setWidth(rect.width())
        geometry.setHeight(rect.height())
        geometry.moveCenter(rect.center())
        geometry.adjust(4, 4, -2, -2)
        self._line_edit.setGeometry(geometry)
        self._line_edit.setText(text)
        self._line_edit.setHidden(False)
        self._line_edit.setFocus()
        self._line_edit.selectAll()

    def _start_editing_tab(self, index: int):
        """Enter edit table name mode."""
        rect = self._tab_rect(index)
        self._current_edit_index = index
        self._move_line_edit(rect, self.tabText(index))
        return None

    def dragEnterEvent(self, e: QtGui.QDragEnterEvent) -> None:
        # This override is necessary for accepting drops from files.
        if isinstance(e.source(), QSubWindowArea):
            e.ignore()
        else:
            e.accept()

    def dropEvent(self, event: QtGui.QDropEvent) -> None:
        mime_data = event.mimeData()
        glob_pos = QtGui.QCursor.pos()
        if QtW.QApplication.widgetAt(glob_pos) is self:
            # dropped on the tabbar outside the existing tabs
            if isinstance(src := event.source(), QSubWindow):
                self._tabbar._process_drop_event(src, -1)
        elif mime_data.hasUrls():
            urls = mime_data.urls()
            for url in urls:
                if url.isLocalFile():
                    path = url.toLocalFile()
                    get_main_window(self).read_file(path)
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


class QStartupWidget(QtW.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        _layout = QtW.QVBoxLayout(self)
        _layout.setContentsMargins(12, 12, 12, 12)
        _layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)

        ctrl = "⌘" if sys.platform == "darwin" else "Ctrl"
        self._open_file_btn = self.make_button("open-file", f"{ctrl}+O")
        self._open_recent_btn = self.make_button("open-recent", f"{ctrl}+K, {ctrl}+R")
        self._load_session_btn = self.make_button("load-session", f"{ctrl}+L")

        _layout.addWidget(self._open_file_btn)
        _layout.addWidget(self._open_recent_btn)
        _layout.addWidget(self._load_session_btn)
        self.setMinimumSize(0, 0)
        return None

    def make_button(self, command_id: str, shortcut: str) -> QClickableLabel:
        def callback():
            get_main_window(self).model_app.commands.execute_command(command_id)

        cmd = get_main_window(self).model_app.commands[command_id]

        label = QClickableLabel(f"{cmd.title} ({shortcut})")
        label.clicked.connect(callback)
        return label
