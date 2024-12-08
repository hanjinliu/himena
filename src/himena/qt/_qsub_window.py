from __future__ import annotations

from contextlib import suppress
from typing import TYPE_CHECKING, Callable, Iterator, cast
from logging import getLogger

from qtpy import QtWidgets as QtW
from qtpy import QtCore, QtGui
from qtpy.QtCore import Qt
from superqt import QIconifyIcon
from superqt.utils import qthrottled

from himena import anchor as _anchor
from himena._descriptors import LocalReaderMethod
from himena._utils import lru_cache, get_display_name
from himena.consts import MenuId
from himena.types import WindowState, WindowRect
from himena.plugins import _checker
from himena.qt._utils import get_main_window, build_qmodel_menu
from himena.qt._qwindow_resize import ResizeState
from himena.qt._qrename import QRenameLineEdit

if TYPE_CHECKING:
    from himena.qt._qmain_window import QMainWindow
    from himena.qt.main_window import MainWindowQt
    from himena.widgets import SubWindow

_LOGGER = getLogger(__name__)


class QSubWindowArea(QtW.QMdiArea):
    area_focused = QtCore.Signal()

    def __init__(self):
        super().__init__()
        self.viewport().setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        self._last_press_pos: QtCore.QPoint | None = None
        self._last_drag_pos: QtCore.QPoint | None = None
        self.setActivationOrder(QtW.QMdiArea.WindowOrder.ActivationHistoryOrder)
        self._last_active_window: QSubWindow | None = None

    def addSubWindow(self, sub_window: QSubWindow):
        super().addSubWindow(sub_window)
        sub_window.show()

    def iter_widgets(self) -> Iterator[QtW.QWidget]:
        """Iterate over all widgets in the sub-window area."""
        for sub_window in self.subWindowList():
            yield sub_window.widget()

    def indexOf(self, sub_window: QSubWindow) -> int:
        return self.subWindowList().index(sub_window)

    def relabel_widgets(self):
        for i, sub_window in enumerate(self.subWindowList()):
            text = f'<span style="color:gray;">{i}</span>'
            sub_window._title_bar._index_label.setText(text)

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
        self.addSubWindow(sub_window)
        sub_window.resize(size + QtCore.QSize(8, 8))
        self.relabel_widgets()
        _checker.call_window_added_callback(widget)
        return sub_window

    def mousePressEvent(self, event: QtGui.QMouseEvent):
        self._last_drag_pos = self._last_press_pos = event.pos()
        if (
            event.button() == Qt.MouseButton.LeftButton
            and event.modifiers() & Qt.KeyboardModifier.ControlModifier
        ):
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        return None

    def mouseMoveEvent(self, event: QtGui.QMouseEvent):
        self._mouse_move_event(event)
        return None

    @qthrottled(timeout=10)
    def _mouse_move_event(self, event: QtGui.QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            if self._last_drag_pos is None:
                return None
            if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                # move all the windows
                dpos = event.pos() - self._last_drag_pos
                for sub_window in self.subWindowList():
                    sub_window.move(sub_window.pos() + dpos)
                self._reanchor_windows()
                self.setCursor(Qt.CursorShape.ClosedHandCursor)
        self._last_drag_pos = event.pos()
        return None

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent):
        # reset cursor state
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self._last_press_pos = self._last_drag_pos = None

        # check if any window is under the cursor
        for sub_window in self.subWindowList():
            if sub_window.rect().contains(sub_window.mapFromParent(event.pos())):
                if not sub_window.is_current():
                    sub_window.set_is_current(True)
                    self.subWindowActivated.emit(sub_window)
                break
        else:
            if event.button() == Qt.MouseButton.RightButton:
                # context menu
                app = get_main_window(self).model_app
                menu = build_qmodel_menu(MenuId.FILE_NEW, app, self)
                menu.exec(event.globalPos())

        return None

    def eventFilter(self, obj, a0: QtCore.QEvent) -> bool:
        if a0.type() == QtCore.QEvent.Type.FocusIn:
            with suppress(RuntimeError):
                if obj is not self:
                    if isinstance(obj, (QtW.QStyle, QtW.QAbstractButton)):
                        return False
                    else:
                        if (
                            win := self.currentSubWindow()
                        ) is not self._last_active_window:
                            self.subWindowActivated.emit(win)
                            self._last_active_window = win
                else:
                    self.area_focused.emit()
                    self._last_active_window = None
                    _LOGGER.debug("TabArea focused.")
        return super().eventFilter(obj, a0)

    def hideEvent(self, a0: QtGui.QHideEvent | None) -> None:
        self._last_drag_pos = self._last_press_pos = None
        return super().hideEvent(a0)

    def resizeEvent(self, a0: QtGui.QResizeEvent) -> None:
        self._reanchor_windows()
        return super().resizeEvent(a0)

    def _reanchor_windows(self):
        """Reanchor all windows if needed (such as minimized windows)."""
        if self.viewMode() != QtW.QMdiArea.ViewMode.SubWindowView:
            return
        parent_geometry = self.viewport().geometry()
        num = 0
        for sub_window in self.subWindowList():
            if sub_window._window_state is WindowState.MIN:
                sub_window._set_minimized(parent_geometry, num)
                num += 1
            elif sub_window._window_state in (WindowState.MAX, WindowState.FULL):
                sub_window.setGeometry(parent_geometry)
            else:
                main_qsize = parent_geometry.size()
                sub_qsize = sub_window.size()
                if rect := sub_window._window_anchor.apply_anchor(
                    (main_qsize.width(), main_qsize.height()),
                    (sub_qsize.width(), sub_qsize.height()),
                ):
                    sub_window.setGeometry(rect.left, rect.top, rect.width, rect.height)

    def _pixmap_resized(
        self,
        size: QtCore.QSize,
        outline: QtGui.QColor | None = None,
    ) -> QtGui.QPixmap:
        return pixmap_resized(self, size, outline)

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
def _icon_window_menu() -> QtGui.QIcon:
    return _get_icon("material-symbols:menu")


@lru_cache(maxsize=1)
def _icon_model_menu() -> QtGui.QIcon:
    return _get_icon("octicon:ai-model-16")


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
        layout.setContentsMargins(1, 0, 1, 1)
        layout.setSpacing(0)
        self.setLayout(layout)


class QSubWindow(QtW.QMdiSubWindow):
    state_change_requested = QtCore.Signal(WindowState)
    rename_requested = QtCore.Signal(str)
    close_requested = QtCore.Signal()

    def __init__(self, widget: QtW.QWidget, title: str):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)

        self._window_state = WindowState.NORMAL
        self._resize_state = ResizeState.NONE
        self._window_anchor: _anchor.WindowAnchor = _anchor.NoAnchor
        self._current_button: int = Qt.MouseButton.NoButton
        self._widget = widget

        self._central_widget = QCentralWidget(self)
        self.setWidget(self._central_widget)

        self._title_bar = QSubWindowTitleBar(self, title)

        self._central_widget.layout().addWidget(self._title_bar)
        spacer = QtW.QWidget()
        spacer.setLayout(QtW.QVBoxLayout())
        spacer.layout().setContentsMargins(4, 4, 4, 4)
        spacer.layout().addWidget(widget)
        self._central_widget.layout().addWidget(spacer)
        self._last_geometry = self.geometry()
        self._anim_geometry = QtCore.QPropertyAnimation(self, b"geometry")
        self.setAcceptDrops(True)

    def _qt_mdiarea(self) -> QMainWindow:
        parent = self
        while parent is not None:
            parent = parent.parentWidget()
            if isinstance(parent, QtW.QMdiArea):
                return parent
        raise ValueError("Could not find the Qt main window.")

    def windowTitle(self) -> str:
        return self._title_bar._title_label.text()

    def setWindowTitle(self, title: str):
        self._title_bar._title_label.setText(title)

    def _subwindow_area(self) -> QSubWindowArea:
        return self.parentWidget().parentWidget()

    def _my_wrapper(self) -> SubWindow:
        return self._widget._himena_widget

    @property
    def state(self) -> WindowState:
        return self._window_state

    def _update_window_state(self, state: WindowState, animate: bool = True):
        state = WindowState(state)
        if self._window_state == state:
            return None
        if self._subwindow_area().viewMode() != QtW.QMdiArea.ViewMode.SubWindowView:
            self._window_state = state
            return None
        if animate:
            _setter = self._set_geometry_animated
        else:
            _setter = self.setGeometry

        if state == WindowState.MIN:
            if self._window_state is WindowState.NORMAL:
                self._store_current_geometry()
            self.resize(124, self._title_bar.height() + 8)
            n_minimized = sum(
                1
                for sub_window in self._subwindow_area().subWindowList()
                if sub_window._window_state is WindowState.MIN
            )
            self._set_minimized(self.parentWidget().geometry(), n_minimized)
        elif state == WindowState.MAX:
            if self._window_state is WindowState.NORMAL:
                self._store_current_geometry()
            _setter(self.parentWidget().geometry())
            self._title_bar._toggle_size_btn.setIcon(_icon_normal())
            self._widget.setVisible(True)
        elif state == WindowState.NORMAL:
            _setter(self._last_geometry)
            self._title_bar._toggle_size_btn.setIcon(_icon_max())
            self._widget.setVisible(True)
            self._title_bar._fix_position()
        elif state == WindowState.FULL:
            if self._window_state is WindowState.NORMAL:
                self._store_current_geometry()
            _setter(self.parentWidget().geometry())
        else:
            raise RuntimeError(f"Invalid window state value: {state}")

        self._title_bar._window_menu_btn.setVisible(state is not WindowState.MIN)
        self._title_bar._model_menu_btn.setVisible(state is not WindowState.MIN)
        self._title_bar.setVisible(state is not WindowState.FULL)
        self._title_bar._minimize_btn.setVisible(state is not WindowState.MIN)
        self._widget.setVisible(state is not WindowState.MIN)
        self._window_state = state
        self._current_button: int = Qt.MouseButton.NoButton
        return None

    def _store_current_geometry(self):
        self._last_geometry = self.geometry()
        _LOGGER.debug("Storing current geometry %r", self._last_geometry)

    def _set_minimized(self, geometry: QtCore.QRect, number: int = 0):
        self.move(2, geometry.height() - (self._title_bar.height() + 8) * (number + 1))
        self._title_bar._toggle_size_btn.setIcon(_icon_normal())
        self._widget.setVisible(False)

    def is_current(self) -> bool:
        return self._title_bar.property("isCurrent")

    def set_is_current(self, is_current: bool):
        """Set the isCurrent state of the sub-window and update styles."""
        self._title_bar.setProperty("isCurrent", is_current)
        self._title_bar.style().unpolish(self._title_bar)
        self._title_bar.style().polish(self._title_bar)

    def event(self, a0: QtCore.QEvent) -> bool:
        if a0.type() == QtCore.QEvent.Type.HoverMove:
            self._mouse_hover_event(a0.pos())
        elif a0.type() == QtCore.QEvent.Type.MouseButtonPress:
            assert isinstance(a0, QtGui.QMouseEvent)
            self._current_button = a0.buttons()
            self._resize_state = self._check_resize_state(a0.pos())
        elif a0.type() == QtCore.QEvent.Type.MouseButtonRelease:
            self._current_button = Qt.MouseButton.NoButton
        return super().event(a0)

    def _check_resize_state(
        self, mouse_pos: QtCore.QPoint, thickness: int = 6, thickness_top: int = 4
    ) -> ResizeState:
        is_left = mouse_pos.x() < thickness
        is_right = mouse_pos.x() > self.width() - thickness
        is_top = mouse_pos.y() < thickness_top
        is_bottom = mouse_pos.y() > self.height() - thickness
        return ResizeState.from_bools(is_left, is_right, is_top, is_bottom)

    @qthrottled(timeout=10)
    def _mouse_hover_event(self, event_pos: QtCore.QPoint):
        # if the cursor is at the edges, set the cursor to resize
        if self._window_state is not WindowState.NORMAL:
            return None
        resize_state = self._check_resize_state(event_pos)
        if self._current_button == Qt.MouseButton.NoButton:
            self.setCursor(resize_state.to_cursor_shape())
        elif self._current_button & Qt.MouseButton.LeftButton:
            # NOTE: Method "minimusSizeHint" represents the minimum size of the widget
            # as a window
            min_size = self._widget.minimumSizeHint().expandedTo(
                self._title_bar.minimumSize()
            )
            max_size = self._widget.maximumSize()
            if self._resize_state.resize_widget(self, event_pos, min_size, max_size):
                # update window anchor
                g = self.geometry()
                main_qsize = self._qt_mdiarea().size()
                self._window_anchor = self._window_anchor.update_for_window_rect(
                    (main_qsize.width(), main_qsize.height()),
                    WindowRect.from_numbers(g.left(), g.top(), g.width(), g.height()),
                )
                _checker.call_window_resized_callback(
                    self._widget, (g.width(), g.height())
                )
        return None

    def _set_geometry_animated(self, rect: QtCore.QRect):
        if self._anim_geometry.state() == QtCore.QAbstractAnimation.State.Running:
            self._anim_geometry.stop()
        self._anim_geometry.setTargetObject(self)
        self._anim_geometry.setPropertyName(b"geometry")
        self._anim_geometry.setStartValue(QtCore.QRect(self.geometry()))
        self._anim_geometry.setEndValue(rect)
        self._anim_geometry.setDuration(60)
        self._anim_geometry.start()

    def _pixmap_resized(
        self,
        size: QtCore.QSize,
        outline: QtGui.QColor | None = None,
    ) -> QtGui.QPixmap:
        return pixmap_resized(self, size, outline)

    def _find_me(self) -> tuple[int, int]:
        return self._find_me_and_main()[0]

    def _find_me_and_main(self) -> tuple[tuple[int, int], MainWindowQt]:
        main = get_main_window(self)
        for i_tab, tab in main.tabs.enumerate():
            for i_win, win in tab.enumerate():
                if win.widget is self._widget:
                    return (i_tab, i_win), main
        raise RuntimeError("Could not find the sub-window in the main window.")

    def dragEnterEvent(self, a0: QtGui.QDragEnterEvent | None) -> None:
        if a0 is not None and isinstance(src := a0.source(), QSubWindow):
            if self._my_wrapper()._is_mergeable_with(src._my_wrapper()):
                a0.accept()
                return None
        a0.ignore()
        return None

    def dropEvent(self, a0: QtGui.QDropEvent | None) -> None:
        if a0 is not None and isinstance(src := a0.source(), QSubWindow):
            # merge data
            if self._my_wrapper()._process_merge_model(src._my_wrapper()):
                a0.accept()
                return None
        a0.ignore()
        return None


class QTitleBarToolButton(QtW.QToolButton):
    def __init__(
        self,
        icon: QtGui.QIcon,
        tooltip: str,
        callback: Callable[[], None],
    ):
        super().__init__()
        self.setIcon(icon)
        self.setToolTip(tooltip)
        self.clicked.connect(callback)

    def _set_size(self, size: int):
        self.setFixedSize(size, size)
        self.setIconSize(QtCore.QSize(size - 1, size - 1))


class QDummyToolButton(QtW.QWidget):
    def _set_size(self, size: int):
        self.setFixedSize(size, size)


class QSubWindowTitleBar(QtW.QFrame):
    def __init__(self, subwindow: QSubWindow, title: str):
        super().__init__()
        self._drag_position: QtCore.QPoint | None = None
        self._is_ctrl_drag: bool = False
        self._is_double_clicking: bool = False
        self._resize_position: QtCore.QPoint | None = None
        self._subwindow = subwindow

        self.setFrameShape(QtW.QFrame.Shape.StyledPanel)
        self.setFrameShadow(QtW.QFrame.Shadow.Raised)
        self.setMinimumWidth(100)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

        self._window_menu_btn = QTitleBarToolButton(
            icon=_icon_window_menu(),
            tooltip="Menu for this window",
            callback=self._show_window_menu,
        )
        if callable(getattr(self._subwindow._widget, "model_type", None)):
            self._model_menu_btn = QTitleBarToolButton(
                icon=_icon_model_menu(),
                tooltip="Menu specific to the model",
                callback=self._show_model_menu,
            )
        else:
            self._model_menu_btn = QDummyToolButton()
            self._model_menu_btn.setVisible(False)

        self._index_label = QtW.QLabel()
        self._index_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignBottom
        )
        _index_font = self._index_label.font()
        _index_font.setPointSize(8)
        _index_font.setBold(True)
        self._index_label.setFont(_index_font)
        self._index_label.setFixedWidth(20)
        self._index_label.setContentsMargins(0, 0, 0, 0)
        self._index_label.setSizePolicy(
            QtW.QSizePolicy.Policy.Fixed, QtW.QSizePolicy.Policy.Fixed
        )

        self._title_label = QtW.QLabel(title)
        self._title_label.setIndent(3)
        self._title_label.setContentsMargins(0, 0, 0, 0)
        self._title_label.setSizePolicy(
            QtW.QSizePolicy.Policy.Expanding, QtW.QSizePolicy.Policy.Fixed
        )

        self._line_edit = QRenameLineEdit(self._title_label)

        @self._line_edit.rename_requested.connect
        def _(new_name: str):
            self._subwindow.rename_requested.emit(new_name)

        self._minimize_btn = QTitleBarToolButton(
            icon=_icon_min(),
            tooltip="Minimize this window",
            callback=self._minimize,
        )
        self._toggle_size_btn = QTitleBarToolButton(
            icon=_icon_max(),
            tooltip="Toggle the size of this window",
            callback=self._toggle_size,
        )
        self._close_btn = QTitleBarToolButton(
            icon=_icon_close(),
            tooltip="Close this window",
            callback=self._close,
        )

        layout = QtW.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(1)
        layout.addWidget(self._window_menu_btn)
        layout.addWidget(self._model_menu_btn)
        layout.addWidget(self._index_label)
        layout.addWidget(self._title_label)
        layout.addWidget(self._minimize_btn, alignment=Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self._toggle_size_btn, alignment=Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self._close_btn, alignment=Qt.AlignmentFlag.AlignRight)

        self.setProperty("isCurrent", False)
        self.setAcceptDrops(True)
        self._set_bar_size(18)

    def _set_bar_size(self, height: int):
        self.setFixedHeight(height)
        self._index_label.setFixedHeight(height)
        self._title_label.setFixedHeight(height)
        self._window_menu_btn._set_size(height - 1)
        self._model_menu_btn._set_size(height - 1)
        self._minimize_btn._set_size(height - 1)
        self._toggle_size_btn._set_size(height - 1)
        self._close_btn._set_size(height - 1)

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
        self._subwindow.state_change_requested.emit(WindowState.MIN)

    def _toggle_size(self):
        if self._subwindow._window_state is WindowState.NORMAL:
            self._subwindow.state_change_requested.emit(WindowState.MAX)
        else:
            self._subwindow.state_change_requested.emit(WindowState.NORMAL)

    def _maximize(self):
        self._subwindow.state_change_requested.emit(WindowState.MAX)

    def _toggle_full_screen(self):
        if self._subwindow._window_state is WindowState.FULL:
            self._subwindow.state_change_requested.emit(WindowState.NORMAL)
        else:
            self._subwindow.state_change_requested.emit(WindowState.FULL)

    def _close(self):
        return self._subwindow.close_requested.emit()

    def _make_tooltip(self):
        qwin = self._subwindow
        attrs: list[str] = [f"<b>Title</b>: {self._title_label.text()}"]
        if hasattr(qwin._widget, "model_type"):
            with suppress(Exception):
                attrs.append(f"<b>Type</b>: {qwin._widget.model_type()}")
        attrs.append(f"<b>Widget</b>: {get_display_name(qwin._widget.__class__)}")
        sub = qwin._my_wrapper()
        attrs.append(f"<b>Save behavior</b>: {sub.save_behavior!r}")
        tooltip = "<br>".join(attrs)
        return tooltip

    def event(self, a0: QtCore.QEvent) -> bool:
        if a0.type() == QtCore.QEvent.Type.ToolTip:
            a0 = cast(QtGui.QHelpEvent, a0)
            QtW.QToolTip.showText(a0.globalPos(), self._make_tooltip())
            return True
        return super().event(a0)

    # drag events for moving the window
    def mousePressEvent(self, event: QtGui.QMouseEvent):
        self._is_ctrl_drag = False
        if self._is_double_clicking:
            return super().mousePressEvent(event)
        if event.button() == Qt.MouseButton.LeftButton:
            _subwin = self._subwindow
            if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                # start dragging subwindow
                self._is_ctrl_drag = True
                drag = QtGui.QDrag(_subwin)
                mime_data = QtCore.QMimeData()
                if isinstance(
                    _meth := self._subwindow._my_wrapper()._widget_data_model_method,
                    LocalReaderMethod,
                ):
                    mime_data.setUrls([QtCore.QUrl(_meth.path.as_uri())])
                drag.setMimeData(mime_data)
                drag.setPixmap(_subwin._pixmap_resized(QtCore.QSize(150, 150)))
                self._subwindow.hide()
                try:
                    drag.exec()
                finally:
                    # NOTE: if subwindow is dropped to another tab, the old one will be
                    # removed from the MdiArea. In this case, the subwindow should not
                    # be shown again.
                    if self._subwindow.parent():
                        self._subwindow.show()
            else:
                if _subwin._window_state == WindowState.MIN:
                    # cannot move minimized window
                    return
            self._store_drag_position(event.globalPos())
        return super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QtGui.QMouseEvent):
        _subwin = self._subwindow
        if (
            event.buttons() == Qt.MouseButton.LeftButton
            and self._drag_position is not None
            and _subwin._resize_state is ResizeState.NONE
            and not self._is_ctrl_drag
        ):
            if _subwin._window_state == WindowState.MAX:
                # change to normal without moving
                self._toggle_size_btn.setIcon(_icon_max())
                _subwin._widget.setVisible(True)
                _subwin._window_state = WindowState.NORMAL
                # restore the last size
                _last_geo = _subwin._last_geometry
                _next_geo = QtCore.QRect(
                    event.pos().x() - _last_geo.width() // 2,
                    event.pos().y() - self.height() // 2,
                    _last_geo.width(),
                    _last_geo.height(),
                )
                _subwin.setGeometry(_next_geo)
                self._store_drag_position(event.globalPos())
            else:
                # drag the subwindow
                new_pos = event.globalPos() - self._drag_position
                offset = self.height() - 4
                if new_pos.y() < -offset:
                    new_pos.setY(-offset)
                _subwin.move(new_pos)

            # update window anchor
            g = _subwin.geometry()
            main_qsize = _subwin._qt_mdiarea().size()
            _subwin._window_anchor = _subwin._window_anchor.update_for_window_rect(
                (main_qsize.width(), main_qsize.height()),
                WindowRect.from_numbers(g.left(), g.top(), g.width(), g.height()),
            )
        return super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent):
        self._is_ctrl_drag = False
        self._is_double_clicking = False
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_position = None
            self._fix_position()
        return super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event: QtGui.QMouseEvent):
        self._is_double_clicking = True
        if event.button() == Qt.MouseButton.LeftButton:
            self._toggle_size()
        return super().mouseDoubleClickEvent(event)

    def wheelEvent(self, event: QtGui.QWheelEvent):
        if event.modifiers() == Qt.KeyboardModifier.NoModifier:
            i_tab, i_win = self._subwindow._find_me()
            main = get_main_window(self)
            sub = main.tabs[i_tab][i_win]
            if event.angleDelta().y() > 0:
                sub._set_rect(sub.rect.resize_relative(1.1, 1.1))
            else:
                sub._set_rect(sub.rect.resize_relative(1 / 1.1, 1 / 1.1))
        return super().wheelEvent(event)

    def dragEnterEvent(self, a0: QtGui.QDragEnterEvent | None) -> None:
        return self._subwindow.dragEnterEvent(a0)

    def dropEvent(self, a0: QtGui.QDropEvent | None) -> None:
        return self._subwindow.dropEvent(a0)

    def _store_drag_position(self, global_pos: QtCore.QPoint):
        subwin = self._subwindow
        self._drag_position = global_pos - subwin.frameGeometry().topLeft()

    def _fix_position(self):
        self_pos = self.mapToGlobal(self._subwindow.rect().topRight())
        parent_pos = self._subwindow.parentWidget().mapToGlobal(QtCore.QPoint(0, 0))
        if self_pos.y() < parent_pos.y():
            self._subwindow.move(self._subwindow.pos().x(), 0)
        if self_pos.x() < parent_pos.x():
            self._subwindow.move(0, self._subwindow.pos().y())

    def _show_model_menu(self):
        model_type = self._subwindow._widget.model_type()
        ui = get_main_window(self)
        model_subtypes = model_type.split(".")
        supertype_menus: list[QtW.QMenu] = []
        _id = f"/model_menu:{model_type}"
        context_menu = build_qmodel_menu(_id, app=ui.model_app.name, parent=self)
        # also add supertype actions
        for num in range(1, len(model_subtypes)):
            _typ = ".".join(model_subtypes[:num])
            _id = f"/model_menu:{_typ}"
            _menu = build_qmodel_menu(_id, app=ui.model_app.name, parent=self)
            _menu.setTitle(f'"{_typ}" menu')
            supertype_menus.append(_menu)
        if supertype_menus:
            context_menu.addSeparator()
            for menu in supertype_menus:
                if not menu.isEmpty():
                    context_menu.addMenu(menu)

        return self._exec_menu_at_button(context_menu, self._model_menu_btn)

    def _show_window_menu(self):
        main = get_main_window(self)
        app = main._model_app

        context_menu = build_qmodel_menu(MenuId.WINDOW, app=app.name, parent=self)
        ctx = main._ctx_keys
        ctx._update(main)
        context_menu.update_from_context(ctx.dict())
        return self._exec_menu_at_button(context_menu, self._window_menu_btn)

    def _exec_menu_at_button(self, menu: QtW.QMenu, btn: QtW.QToolButton):
        pos_local = btn.rect().bottomLeft()
        pos_global = btn.mapToGlobal(pos_local)
        menu.exec(pos_global)
        return None


def pixmap_resized(
    widget: QtW.QWidget,
    size: QtCore.QSize,
    outline: QtGui.QColor | None = None,
) -> QtGui.QPixmap:
    pixmap = widget.grab().scaled(
        size,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )
    if outline is not None:
        painter = QtGui.QPainter(pixmap)
        painter.setPen(QtGui.QPen(outline, 2))
        painter.drawRect(pixmap.rect())
        painter.end()
    return pixmap
