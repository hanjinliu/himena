from __future__ import annotations
from typing import TYPE_CHECKING, Iterator, Generic, TypeVar
from timeit import default_timer as timer
from qtpy import QtWidgets as QtW
from qtpy import QtCore, QtGui
from superqt import QIconifyIcon
from royalapp.types import SubWindowState
from royalapp.qt._qwindow_resize import ResizeState

_T = TypeVar("_T", bound=QtW.QWidget)


class QSubWindowArea(QtW.QMdiArea):
    def __init__(self):
        super().__init__()

    def addSubWindow(self, sub_window: QSubWindow):
        super().addSubWindow(sub_window)
        sub_window.show()

    def iter_widgets(self) -> Iterator[QtW.QWidget]:
        """Iterate over all widgets in the sub-window area."""
        for sub_window in self.subWindowList():
            yield sub_window.widget()

    def add_widget(
        self,
        widget: _T,
        *,
        title: str | None = None,
    ) -> QSubWindow[_T]:
        """
        Add a widget to the sub window.

        Parameters
        ----------
        widget : QtW.QWidget
            Widget to add.
        title : str, optional
            Title of the sub-window. If not given, its name will be automatically
            generated.

        Returns
        -------
        QSubWindow
            A sub-window widget. The added widget is available by calling
            `main_widget()` method.
        """
        if title is None:
            title = widget.objectName() or "Window"
        if not isinstance(widget, QtW.QWidget):
            raise TypeError(
                f"`widget` must be a QtW.QWidget instance, got {type(widget)}."
            )
        size = widget.size()
        sub_window = QSubWindow(widget, self._coerce_window_title(title))
        sub_window.resize(size)
        nwindows = len(self.subWindowList())
        self.addSubWindow(sub_window)
        sub_window.move(4 + 24 * nwindows, 4 + 24 * nwindows)
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

    def _coerce_window_title(self, title: str) -> str:
        existing = {sub_window.windowTitle() for sub_window in self.subWindowList()}
        title_original = title
        count = 0
        while title in existing:
            title = f"{title_original}-{count}"
            count += 1
        return title

    if TYPE_CHECKING:

        def subWindowList(self) -> list[QSubWindow]: ...
        def activeSubWindow(self) -> QSubWindow: ...
        def currentSubWindow(self) -> QSubWindow: ...


_ICON_MIN = QIconifyIcon("material-symbols:minimize-rounded")
_ICON_MAX = QIconifyIcon("material-symbols:crop-5-4-outline")
_ICON_CLOSE = QIconifyIcon("material-symbols:close-rounded")
_ICON_NORMAL = QIconifyIcon("material-symbols:filter-none-outline-rounded", rotate=180)


class QSubWindow(QtW.QMdiSubWindow, Generic[_T]):
    def __init__(self, widget: _T, title: str):
        super().__init__()
        self.setWindowFlags(QtCore.Qt.WindowType.FramelessWindowHint)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose)
        # add shadow effect
        self._shadow_effect = QtW.QGraphicsDropShadowEffect()
        self._shadow_effect.setBlurRadius(14)
        self._shadow_effect.setColor(QtGui.QColor(0, 0, 0, 100))
        self._shadow_effect.setOffset(0, 0)
        self.setGraphicsEffect(self._shadow_effect)

        self._window_state = SubWindowState.NORMAL
        self._resize_state = ResizeState.NONE
        self._current_button: int = QtCore.Qt.MouseButton.NoButton
        self._last_hovered = timer()

        _central_widget = QtW.QWidget()
        layout = QtW.QVBoxLayout()
        pad = 4
        layout.setContentsMargins(pad, pad, pad, pad)
        layout.setSpacing(0)
        _central_widget.setLayout(layout)
        self.setWidget(_central_widget)

        self._title_bar = QSubWindowTitleBar(self, title)

        layout.addWidget(self._title_bar)
        layout.addWidget(widget)
        self._last_geometry = self.geometry()

        # self._graphics_effect = QtW.QGraphicsDropShadowEffect()  # TODO
        self._widget = widget
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_Hover, True)

    def main_widget(self) -> _T:
        return self._widget

    def windowTitle(self) -> str:
        return self._title_bar._title_label.text()

    def setWindowTitle(self, title: str):
        self._title_bar._title_label.setText(title)

    def _subwindow_area(self) -> QSubWindowArea:
        return self.parentWidget().parentWidget()

    @property
    def state(self) -> SubWindowState:
        return self._window_state

    @state.setter
    def state(self, state: SubWindowState):
        state = SubWindowState(state)
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
                self._title_bar._toggle_size_button.setIcon(_ICON_NORMAL)
                self._widget.setVisible(True)
            case SubWindowState.NORMAL:
                self.setGeometry(self._last_geometry)
                self._title_bar._toggle_size_button.setIcon(_ICON_MAX)
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
        self._title_bar._toggle_size_button.setIcon(_ICON_NORMAL)
        self._widget.setVisible(False)

    def move_over(self, other: QSubWindow, dx: int = 36, dy: int = 36):
        rect = other.geometry()
        rect.translate(dx, dy)
        self.setGeometry(rect)
        return self

    def keyPressEvent(self, a0: QtGui.QKeyEvent | None) -> None:
        if a0.key() == QtCore.Qt.Key.Key_F11:
            self._title_bar._toggle_full_screen()

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

    def _mouse_hover_event(self, event_pos: QtCore.QPoint):
        # if the cursor is at the edges, set the cursor to resize
        if self.state is not SubWindowState.NORMAL:
            return
        current_time = timer()
        if current_time - self._last_hovered < 0.1:
            return
        self._last_hovered = current_time
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


class QSubWindowTitleBar(QtW.QFrame):
    def __init__(self, subwindow: QSubWindow[_T], title: str):
        super().__init__()
        self.setFrameShape(QtW.QFrame.Shape.StyledPanel)
        self.setFrameShadow(QtW.QFrame.Shadow.Raised)
        height = 18
        self.setFixedHeight(height)
        self.setMinimumWidth(100)
        self._title = title
        self._title_label = QtW.QLabel(title)
        self._title_label.setIndent(3)
        self._title_label.setFixedHeight(height)
        self._title_label.setContentsMargins(0, 0, 0, 0)
        self._title_label.setSizePolicy(
            QtW.QSizePolicy.Policy.Expanding, QtW.QSizePolicy.Policy.Fixed
        )

        self._minimize_button = QtW.QToolButton()
        self._minimize_button.clicked.connect(self._minimize)
        self._minimize_button.setToolTip("Minimize this window")
        self._minimize_button.setFixedSize(height, height)
        self._minimize_button.setIcon(_ICON_MIN)
        self._minimize_button.setIconSize(QtCore.QSize(height - 2, height - 2))

        self._toggle_size_button = QtW.QToolButton()
        self._toggle_size_button.clicked.connect(self._toggle_size)
        self._toggle_size_button.setToolTip("Toggle the size of this window")
        self._toggle_size_button.setFixedSize(height, height)
        self._toggle_size_button.setIcon(_ICON_MAX)
        self._toggle_size_button.setIconSize(QtCore.QSize(height - 2, height - 2))

        self._close_button = QtW.QToolButton()
        self._close_button.clicked.connect(self._close)
        self._close_button.setToolTip("Close this window")
        self._close_button.setFixedSize(height, height)
        self._close_button.setIcon(_ICON_CLOSE)
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
        self._subwindow.close()

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
                self._toggle_size_button.setIcon(_ICON_MAX)
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
