from __future__ import annotations
from typing import TYPE_CHECKING, Iterator, Callable, TypeVar
from functools import lru_cache
from qtpy import QtWidgets as QtW
from qtpy import QtCore, QtGui
from superqt import QIconifyIcon
from superqt.utils import qthrottled
from royalapp.types import SubWindowState
from royalapp.qt._utils import get_main_window
from royalapp.qt._qwindow_resize import ResizeState
from royalapp.qt._qrename import QRenameLineEdit

if TYPE_CHECKING:
    _F = TypeVar("_F", bound=Callable)

    def lru_cache(maxsize: int = 128, typed: bool = False) -> Callable[[_F], _F]: ...


class QSubWindowArea(QtW.QMdiArea):
    def __init__(self):
        super().__init__()
        self.viewport().setFocusPolicy(QtCore.Qt.FocusPolicy.ClickFocus)

    def addSubWindow(self, sub_window: QSubWindow):
        super().addSubWindow(sub_window)
        sub_window.show()

    def iter_widgets(self) -> Iterator[QtW.QWidget]:
        """Iterate over all widgets in the sub-window area."""
        for sub_window in self.subWindowList():
            yield sub_window.widget()

    def indexOf(self, sub_window: QSubWindow) -> int:
        return self.subWindowList().index(sub_window)

    def add_widget(
        self,
        widget: QtW.QWidget,
        title: str | None = None,
    ) -> QSubWindow:
        if title is None:
            title = widget.objectName() or "Window"
        if not isinstance(widget, QtW.QWidget):
            raise TypeError(
                f"`widget` must be a QtW.QWidget instance, got {type(widget)}."
            )
        size = widget.sizeHint().expandedTo(QtCore.QSize(160, 120))
        sub_window = QSubWindow(widget, title)
        nwindows = len(self.subWindowList())
        self.addSubWindow(sub_window)
        sub_window.resize(size + QtCore.QSize(8, 8))
        sub_window.move(4 + 24 * (nwindows % 5), 4 + 24 * (nwindows % 5))
        return sub_window

    def _reanchor_windows(self):
        if self.viewMode() != QtW.QMdiArea.ViewMode.SubWindowView:
            return
        parent_geometry = self.viewport().geometry()
        num = 0
        for sub_window in self.subWindowList():
            if sub_window.state is SubWindowState.MIN:
                sub_window._set_minimized(parent_geometry, num)
                num += 1
            elif sub_window.state in (SubWindowState.MAX, SubWindowState.FULL):
                sub_window.setGeometry(parent_geometry)

    if TYPE_CHECKING:

        def subWindowList(self) -> list[QSubWindow]: ...
        def activeSubWindow(self) -> QSubWindow: ...
        def currentSubWindow(self) -> QSubWindow | None: ...


def _get_icon(name: str, rotate=None):
    try:
        return QIconifyIcon(name, rotate=rotate)
    except OSError:
        return QtGui.QIcon()


@lru_cache(maxsize=1)
def _icon_min() -> QtGui.QIcon:
    return _get_icon("material-symbols:minimize-rounded")


@lru_cache(maxsize=1)
def _icon_max() -> QtGui.QIcon:
    return _get_icon("material-symbols:crop-5-4-outline")


@lru_cache(maxsize=1)
def _icon_close() -> QtGui.QIcon:
    return _get_icon("material-symbols:close-rounded")


@lru_cache(maxsize=1)
def _icon_normal() -> QtGui.QIcon:
    return _get_icon("material-symbols:filter-none-outline-rounded", rotate=180)


class QCentralWidget(QtW.QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        layout = QtW.QVBoxLayout()
        pad = 4
        layout.setContentsMargins(pad, pad, pad, pad)
        layout.setSpacing(0)
        self.setLayout(layout)


class QSubWindow(QtW.QMdiSubWindow):
    state_changed = QtCore.Signal(SubWindowState)
    closed = QtCore.Signal()

    def __init__(self, widget: QtW.QWidget, title: str):
        super().__init__()
        self.setWindowFlags(QtCore.Qt.WindowType.FramelessWindowHint)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_Hover, True)

        self._window_state = SubWindowState.NORMAL
        self._resize_state = ResizeState.NONE
        self._current_button: int = QtCore.Qt.MouseButton.NoButton
        self._widget = widget

        self._central_widget = QCentralWidget(self)
        self.setWidget(self._central_widget)

        self._title_bar = QSubWindowTitleBar(self, title)

        self._central_widget.layout().addWidget(self._title_bar)
        self._central_widget.layout().addWidget(widget)
        self._last_geometry = self.geometry()

        # BUG: this causes the window to be unresponsive sometimes
        # add shadow effect
        # self._shadow_effect = QtW.QGraphicsDropShadowEffect(self)
        # self._shadow_effect.setBlurRadius(14)
        # self._shadow_effect.setColor(QtGui.QColor(0, 0, 0, 100))
        # self._shadow_effect.setOffset(0, 0)
        # self.setGraphicsEffect(self._shadow_effect)

    def main_widget(self) -> QtW.QWidget:
        return self._widget

    def windowTitle(self) -> str:
        return self._title_bar._title_label.text()

    def setWindowTitle(self, title: str):
        self._title_bar._title_label.setText(title)
        self._title_bar.setToolTip(title)

    def _subwindow_area(self) -> QSubWindowArea:
        return self.parentWidget().parentWidget()

    @property
    def state(self) -> SubWindowState:
        return self._window_state

    @state.setter
    def state(self, state: SubWindowState):
        state = SubWindowState(state)
        self.state_changed.emit(state)
        if self._subwindow_area().viewMode() != QtW.QMdiArea.ViewMode.SubWindowView:
            self._window_state = state
            return None
        match state:
            case SubWindowState.MIN:
                if self.state is SubWindowState.NORMAL:
                    self._last_geometry = self.geometry()
                self.resize(124, self._title_bar.height() + 8)
                n_minimized = sum(
                    1
                    for sub_window in self._subwindow_area().subWindowList()
                    if sub_window.state is SubWindowState.MIN
                )
                self._set_minimized(self.parentWidget().geometry(), n_minimized)
            case SubWindowState.MAX:
                if self.state is SubWindowState.NORMAL:
                    self._last_geometry = self.geometry()
                self.setGeometry(self.parentWidget().geometry())
                self._title_bar._toggle_size_button.setIcon(_icon_normal())
                self._widget.setVisible(True)
            case SubWindowState.NORMAL:
                self.setGeometry(self._last_geometry)
                self._title_bar._toggle_size_button.setIcon(_icon_max())
                self._widget.setVisible(True)
                if self._title_bar.is_upper_than_area():
                    self.move(self.pos().x(), 0)
            case SubWindowState.FULL:
                if self.state is SubWindowState.NORMAL:
                    self._last_geometry = self.geometry()
                self.setGeometry(self.parentWidget().geometry())
        self._title_bar.setVisible(state is not SubWindowState.FULL)
        self._title_bar._minimize_button.setVisible(state is not SubWindowState.MIN)
        self._widget.setVisible(state is not SubWindowState.MIN)
        self._window_state = state
        self._current_button: int = QtCore.Qt.MouseButton.NoButton
        return None

    def _set_minimized(self, geometry: QtCore.QRect, number: int = 0):
        self.move(2, geometry.height() - (self._title_bar.height() + 8) * (number + 1))
        self._title_bar._toggle_size_button.setIcon(_icon_normal())
        self._widget.setVisible(False)

    def move_over(self, other: QSubWindow, dx: int = 36, dy: int = 36):
        rect = other.geometry()
        rect.translate(dx, dy)
        self.setGeometry(rect)
        return self

    def keyPressEvent(self, a0: QtGui.QKeyEvent | None) -> None:
        if a0.key() == QtCore.Qt.Key.Key_F11:
            self._title_bar._toggle_full_screen()
        return super().keyPressEvent(a0)

    def event(self, a0: QtCore.QEvent) -> bool:
        if a0.type() == QtCore.QEvent.Type.HoverMove:
            self._mouse_hover_event(a0.pos())
        elif a0.type() == QtCore.QEvent.Type.MouseButtonPress:
            assert isinstance(a0, QtGui.QMouseEvent)
            self._current_button = a0.buttons()
            self._resize_state = self._check_resize_state(a0.pos())
        elif a0.type() == QtCore.QEvent.Type.MouseButtonRelease:
            self._current_button = QtCore.Qt.MouseButton.NoButton
        return super().event(a0)

    def _check_resize_state(
        self,
        mouse_pos: QtCore.QPoint,
        thickness: int = 6,
    ) -> ResizeState:
        is_left = mouse_pos.x() < thickness
        is_right = mouse_pos.x() > self.width() - thickness
        is_top = mouse_pos.y() < thickness
        is_bottom = mouse_pos.y() > self.height() - thickness
        return ResizeState.from_bools(is_left, is_right, is_top, is_bottom)

    @qthrottled(timeout=10)
    def _mouse_hover_event(self, event_pos: QtCore.QPoint):
        # if the cursor is at the edges, set the cursor to resize
        if self.state is not SubWindowState.NORMAL:
            return None
        resize_state = self._check_resize_state(event_pos)
        if self._current_button == QtCore.Qt.MouseButton.NoButton:
            self.setCursor(resize_state.to_cursor_shape())
        elif self._current_button & QtCore.Qt.MouseButton.LeftButton:
            min_size = self._widget.minimumSize().expandedTo(
                self._title_bar.minimumSize()
            )
            max_size = self._widget.maximumSize()
            self._resize_state.resize_widget(self, event_pos, min_size, max_size)
        return None

    def _close_me(self, confirm: bool = False):
        if confirm:
            is_modified = getattr(self.main_widget(), "is_modified", None)
            if callable(is_modified) and is_modified():
                _yes = QtW.QMessageBox.StandardButton.Yes
                _no = QtW.QMessageBox.StandardButton.No
                ok = (
                    QtW.QMessageBox.question(
                        self,
                        "Close Window",
                        "Data is not saved. Are you sure to close this window?",
                        _yes | _no,
                    )
                    == _yes
                )
                if not ok:
                    return
        self.close()
        self.closed.emit()
        return None


class QSubWindowTitleBar(QtW.QFrame):
    def __init__(self, subwindow: QSubWindow, title: str):
        super().__init__()
        self.setFrameShape(QtW.QFrame.Shape.StyledPanel)
        self.setFrameShadow(QtW.QFrame.Shadow.Raised)
        height = 18
        self.setFixedHeight(height)
        self.setMinimumWidth(100)
        self.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

        self._title = title
        self._title_label = QtW.QLabel(title)
        self._title_label.setIndent(3)
        self._title_label.setFixedHeight(height)
        self._title_label.setContentsMargins(0, 0, 0, 0)
        self._title_label.setSizePolicy(
            QtW.QSizePolicy.Policy.Expanding, QtW.QSizePolicy.Policy.Fixed
        )

        self._line_edit = QRenameLineEdit(self._title_label)

        @self._line_edit.rename_requested.connect
        def _(new_name: str):
            if tab := get_main_window(self).tabs.current():
                new_name = tab._coerce_window_title(new_name)
            self._title_label.setText(new_name)

        self._minimize_button = QtW.QToolButton()
        self._minimize_button.clicked.connect(self._minimize)
        self._minimize_button.setToolTip("Minimize this window")
        self._minimize_button.setFixedSize(height, height)
        self._minimize_button.setIcon(_icon_min())
        self._minimize_button.setIconSize(QtCore.QSize(height - 2, height - 2))

        self._toggle_size_button = QtW.QToolButton()
        self._toggle_size_button.clicked.connect(self._toggle_size)
        self._toggle_size_button.setToolTip("Toggle the size of this window")
        self._toggle_size_button.setFixedSize(height, height)
        self._toggle_size_button.setIcon(_icon_max())
        self._toggle_size_button.setIconSize(QtCore.QSize(height - 2, height - 2))

        self._close_button = QtW.QToolButton()
        self._close_button.clicked.connect(self._close)
        self._close_button.setToolTip("Close this window")
        self._close_button.setFixedSize(height, height)
        self._close_button.setIcon(_icon_close())
        self._close_button.setIconSize(QtCore.QSize(height - 2, height - 2))

        layout = QtW.QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(1)
        layout.addWidget(self._title_label)
        layout.addWidget(
            self._minimize_button, alignment=QtCore.Qt.AlignmentFlag.AlignRight
        )
        layout.addWidget(
            self._toggle_size_button, alignment=QtCore.Qt.AlignmentFlag.AlignRight
        )
        layout.addWidget(
            self._close_button, alignment=QtCore.Qt.AlignmentFlag.AlignRight
        )
        self.setLayout(layout)

        self._drag_position: QtCore.QPoint | None = None
        self._resize_position: QtCore.QPoint | None = None
        self._subwindow = subwindow

    def _show_context_menu(self):
        # TODO: use app_model.Action
        menu = QtW.QMenu(self)
        menu.addAction("Rename", self._start_renaming)
        menu.addAction("Minimize", self._minimize)
        menu.addAction("Maximize", self._maximize)
        menu.addAction("Toggle full screen", self._toggle_full_screen)
        menu.addAction("Close", self._close)
        menu.move(QtGui.QCursor.pos())
        menu.exec_()

    def _start_renaming(self):
        self._line_edit.show()
        self._move_line_edit(self._title_label.rect(), self._title_label.text())

    def _move_line_edit(
        self,
        rect: QtCore.QRect,
        text: str,
    ) -> QtW.QLineEdit:
        geometry = self._line_edit.geometry()
        geometry.setWidth(rect.width())
        geometry.setHeight(rect.height())
        geometry.moveCenter(rect.center())
        self._line_edit.setGeometry(geometry)
        self._line_edit.setText(text)
        self._line_edit.setHidden(False)
        self._line_edit.setFocus()
        self._line_edit.selectAll()

    def _minimize(self):
        self._subwindow.state = SubWindowState.MIN

    def _toggle_size(self):
        if self._subwindow.state is SubWindowState.NORMAL:
            self._subwindow.state = SubWindowState.MAX
        else:
            self._subwindow.state = SubWindowState.NORMAL

    def _maximize(self):
        self._subwindow.state = SubWindowState.MAX

    def _toggle_full_screen(self):
        if self._subwindow.state is SubWindowState.FULL:
            self._subwindow.state = SubWindowState.NORMAL
        else:
            self._subwindow.state = SubWindowState.FULL

    def _close(self):
        return self._subwindow._close_me(confirm=True)

    # drag events for moving the window
    def mousePressEvent(self, event: QtGui.QMouseEvent):
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            if self._subwindow.state == SubWindowState.MIN:
                # cannot move minimized window
                return
            self._drag_position = (
                event.globalPos() - self._subwindow.frameGeometry().topLeft()
            )
        return super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QtGui.QMouseEvent):
        if (
            event.buttons() == QtCore.Qt.MouseButton.LeftButton
            and self._drag_position is not None
            and self._subwindow._resize_state is ResizeState.NONE
        ):
            if self._subwindow.state == SubWindowState.MAX:
                # change to normal without moving
                self._toggle_size_button.setIcon(_icon_max())
                self._subwindow._widget.setVisible(True)
                self._subwindow._window_state = SubWindowState.NORMAL
            new_pos = event.globalPos() - self._drag_position
            offset = self.height() - 4
            if new_pos.y() < -offset:
                new_pos.setY(-offset)
            self._subwindow.move(new_pos)
        return super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent):
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self._drag_position = None
            if self.is_upper_than_area():
                self._subwindow.state = SubWindowState.MAX
        return super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event: QtGui.QMouseEvent):
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self._toggle_size()
        return super().mouseDoubleClickEvent(event)

    def is_upper_than_area(self) -> bool:
        self_pos = self.mapToGlobal(self._subwindow.rect().topLeft())
        parent_pos = self._subwindow.parentWidget().mapToGlobal(QtCore.QPoint(0, 0))
        return self_pos.y() < parent_pos.y()
