from __future__ import annotations

from enum import Enum, auto
from contextlib import suppress
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Iterator, cast
from logging import getLogger

from app_model.types import MenuItem
from app_model.backends.qt import QCommandRuleAction
from qtpy import QtWidgets as QtW
from qtpy import QtCore, QtGui
from qtpy.QtCore import Qt
from superqt import QIconifyIcon
from superqt.utils import qthrottled

from himena.workflow import LocalReaderMethod
from himena._utils import get_display_name
from himena.utils.misc import lru_cache
from himena.consts import MenuId
from himena.types import DragDataModel, WindowState, WindowRect, Size
from himena.plugins import _checker
from himena.utils.window_rect import ResizeState
from himena.qt._utils import get_main_window, build_qmodel_menu
from himena.qt._qrename import QRenameLineEdit
from himena import _drag

if TYPE_CHECKING:
    from PyQt6 import QtWidgets as QtW
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
        self._last_active_window_id: QSubWindow | None = None

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
        """Update the 0, 1, 2... labels in the sub-windows."""
        for i, sub_window in enumerate(self.subWindowList()):
            sub_window._title_bar._index_label.setText(str(i))

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
        size = widget.sizeHint().expandedTo(QtCore.QSize(160, 120)) + QtCore.QSize(8, 8)
        sub_window = QSubWindow(widget, title)
        self.addSubWindow(sub_window)
        sub_window.resize(size)
        self.relabel_widgets()
        return sub_window

    def mousePressEvent(self, event: QtGui.QMouseEvent):
        self._last_drag_pos = self._last_press_pos = event.pos()
        if (
            event.buttons() & Qt.MouseButton.LeftButton
            and event.modifiers() & Qt.KeyboardModifier.ControlModifier
        ):
            self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def mouseMoveEvent(self, event: QtGui.QMouseEvent):
        self._mouse_move_event(event)

    def _mouse_move_event(self, event: QtGui.QMouseEvent):
        if event.buttons() & Qt.MouseButton.LeftButton:
            if self._last_drag_pos is None:
                return None
            if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                # move all the windows
                dpos = event.pos() - self._last_drag_pos
                for sub_window in self.subWindowList():
                    sub_window.move(sub_window.pos() + dpos)
                self.setCursor(Qt.CursorShape.ClosedHandCursor)
        self._last_drag_pos = event.pos()

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

    def eventFilter(self, obj, a0: QtCore.QEvent) -> bool:
        if a0.type() == QtCore.QEvent.Type.FocusIn:
            with suppress(RuntimeError):
                if obj is not self:
                    if isinstance(obj, (QtW.QStyle, QtW.QAbstractButton, QtW.QMenuBar)):
                        return False
                    else:
                        if self._last_active_window_id is None and (
                            win := self.currentSubWindow()
                        ):
                            self.subWindowActivated.emit(win)
                            self._last_active_window_id = win._my_wrapper()._identifier
                            _LOGGER.debug("QSubWindowArea.eventFilter: Window focused.")
                else:
                    self._set_area_focused()
                    _LOGGER.debug("QSubWindowArea.eventFilter: TabArea focused.")
        try:
            return super().eventFilter(obj, a0)
        except RuntimeError:  # wrapped object deleted
            return False

    def _set_area_focused(self):
        self.area_focused.emit()
        self._last_active_window_id = None

    def hideEvent(self, a0: QtGui.QHideEvent | None) -> None:
        self._last_drag_pos = self._last_press_pos = None
        return super().hideEvent(a0)

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


def _get_icon(name: str, rotate=None, color=None):
    try:
        return QIconifyIcon(name, rotate=rotate, color=color)
    except OSError:
        return QtGui.QIcon()


class TitleIconId(Enum):
    WINDOW_MENU = auto()
    MODEL_MENU = auto()
    ACTION_HINT = auto()
    MIN = auto()
    MAX = auto()
    CLOSE = auto()
    NORMAL = auto()


@lru_cache(maxsize=20)
def _icon_for_id(icon_id: TitleIconId, color: str) -> QtGui.QIcon:
    if icon_id is TitleIconId.WINDOW_MENU:
        return _get_icon("material-symbols:menu", color=color)
    elif icon_id is TitleIconId.MODEL_MENU:
        return _get_icon("octicon:ai-model-16", color=color)
    elif icon_id is TitleIconId.ACTION_HINT:
        return _get_icon("ant-design:bulb-outlined", color=color)
    elif icon_id is TitleIconId.MIN:
        return _get_icon("material-symbols:minimize-rounded", color=color)
    elif icon_id is TitleIconId.MAX:
        return _get_icon("material-symbols:crop-5-4-outline", color=color)
    elif icon_id is TitleIconId.CLOSE:
        return _get_icon("material-symbols:close-rounded", color=color)
    elif icon_id is TitleIconId.NORMAL:
        return _get_icon(
            "material-symbols:filter-none-outline-rounded", rotate=180, color=color
        )
    else:
        raise ValueError(f"Invalid icon id: {icon_id}")


class QCentralWidget(QtW.QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        layout = QtW.QVBoxLayout(self)
        layout.setContentsMargins(1, 0, 1, 1)
        layout.setSpacing(0)


class QSubWindow(QtW.QMdiSubWindow):
    state_change_requested = QtCore.Signal(WindowState)
    rename_requested = QtCore.Signal(str)
    close_requested = QtCore.Signal()

    def __init__(self, widget: QtW.QWidget, title: str, icon_color: str = "black"):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)

        self._window_state = WindowState.NORMAL
        self._resize_state = ResizeState.NONE
        self._widget = widget
        self._current_icon_color = icon_color

        self._central_widget = QCentralWidget(self)
        self.setWidget(self._central_widget)

        self._title_bar = QSubWindowTitleBar(self, title)

        self._central_widget.layout().addWidget(self._title_bar)
        spacer = QtW.QWidget()
        layout = QtW.QVBoxLayout(spacer)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.addWidget(widget)
        self._central_widget.layout().addWidget(spacer)
        self._last_geometry = self.geometry()
        self._anim_geometry = QtCore.QPropertyAnimation(self, b"geometry")
        self.setAcceptDrops(True)

        min_qsize = widget.minimumSizeHint().expandedTo(self._title_bar.minimumSize())
        max_qsize = widget.maximumSize()
        self._min_size = Size(min_qsize.width(), min_qsize.height())
        self._max_size = Size(max_qsize.width(), max_qsize.height())

    def _qt_mdiarea(self) -> QSubWindowArea:
        parent = self
        while parent is not None:
            parent = parent.parentWidget()
            if isinstance(parent, QSubWindowArea):
                return parent
        raise ValueError("Could not find the Qt main window.")

    def windowTitle(self) -> str:
        return self._title_bar._title_label.text()

    def setWindowTitle(self, title: str):
        self._title_bar._title_label.setText(title)

    def _my_wrapper(self) -> SubWindow:
        return self._widget._himena_widget

    @property
    def state(self) -> WindowState:
        return self._window_state

    def _set_icon_color(self, color: str):
        self._title_bar._set_icon_color(color)
        self._current_icon_color = color

    def _update_window_state(self, state: WindowState, animate: bool = True):
        state = WindowState(state)
        g_last = Size(self._last_geometry.width(), self._last_geometry.height())
        if self._window_state == state:
            return None
        if self._qt_mdiarea().viewMode() != QtW.QMdiArea.ViewMode.SubWindowView:
            self._window_state = state
            return None
        if animate:
            _setter = self._set_geometry_animated
        else:
            _setter = self.setGeometry
        g_parent = self.parentWidget().geometry()
        g_size = Size(g_parent.width(), g_parent.height())
        if state == WindowState.MIN:
            if self._window_state is WindowState.NORMAL:
                self._store_current_geometry()
            self.resize(124, self._title_bar.height() + 8)
            n_minimized = sum(
                1
                for sub_window in self._qt_mdiarea().subWindowList()
                if sub_window._window_state is WindowState.MIN
            )
            self._set_minimized(g_parent, n_minimized)
        elif state == WindowState.MAX:
            if self._window_state is WindowState.MIN:
                size_old = g_last
            elif self._window_state is WindowState.NORMAL:
                size_old = Size(self.size().width(), self.size().height())
                self._store_current_geometry()
            else:
                size_old = g_size
            _setter(g_parent)
            self._title_bar._toggle_size_btn.setIcon(
                _icon_for_id(TitleIconId.NORMAL, self._current_icon_color)
            )
            self._widget.setVisible(True)
            _checker.call_widget_resized_callback(
                self._my_wrapper().widget, size_old, g_size
            )
        elif state == WindowState.NORMAL:
            if self._window_state is WindowState.MIN:
                size_old = g_last
            else:
                size_old = g_size
            _setter(self._last_geometry)
            self._title_bar._toggle_size_btn.setIcon(
                _icon_for_id(TitleIconId.MAX, self._current_icon_color)
            )
            self._widget.setVisible(True)
            self._title_bar._fix_position()
            _checker.call_widget_resized_callback(
                self._my_wrapper().widget, size_old, g_last
            )
        elif state == WindowState.FULL:
            if self._window_state is WindowState.MIN:
                size_old = g_last
            elif self._window_state is WindowState.NORMAL:
                size_old = Size(self.size().width(), self.size().height())
                self._store_current_geometry()
            else:
                size_old = g_size
            _setter(g_parent)
            _checker.call_widget_resized_callback(
                self._my_wrapper().widget, size_old, g_last
            )
        else:  # pragma: no cover
            raise RuntimeError(f"Invalid window state value: {state}")

        self._title_bar._window_menu_btn.setVisible(state is not WindowState.MIN)
        self._title_bar._model_menu_btn.setVisible(state is not WindowState.MIN)
        self._title_bar.setVisible(state is not WindowState.FULL)
        self._title_bar._minimize_btn.setVisible(state is not WindowState.MIN)
        self._widget.setVisible(state is not WindowState.MIN)
        self._window_state = state
        return None

    def _store_current_geometry(self):
        self._last_geometry = self.geometry()
        _LOGGER.debug("Storing current geometry %r", self._last_geometry)

    def _set_minimized(self, geometry: QtCore.QRect, number: int = 0):
        self.move(2, geometry.height() - (self._title_bar.height() + 8) * (number + 1))
        self._title_bar._toggle_size_btn.setIcon(
            _icon_for_id(TitleIconId.NORMAL, self._current_icon_color)
        )
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
            self._resize_state = self._check_resize_state(a0.pos())
        elif a0.type() == QtCore.QEvent.Type.MouseButtonRelease:
            self._resize_state = ResizeState.NONE
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
        current_button = QtW.QApplication.mouseButtons()
        if current_button == Qt.MouseButton.NoButton:
            self.setCursor(CURSOR_SHAPE_MAP[resize_state])
        elif current_button & Qt.MouseButton.LeftButton:
            # NOTE: Method "minimusSizeHint" represents the minimum size of the widget
            # as a window
            rect = self.geometry()
            if new_rect := self._resize_state.resize_widget(
                WindowRect(rect.left(), rect.top(), rect.width(), rect.height()),
                mouse_pos=(event_pos.x(), event_pos.y()),
                min_size=self._min_size,
                max_size=self._max_size,
            ):
                subwin = self._my_wrapper()
                size_old = Size(rect.width(), rect.height())

                # update window rect
                subwin.rect = new_rect

                # update window anchor
                main_qsize = self._qt_mdiarea().size()
                subwin.anchor = subwin.anchor.update_for_window_rect(
                    (main_qsize.width(), main_qsize.height()),
                    new_rect,
                )
                _checker.call_widget_resized_callback(
                    self._my_wrapper().widget,
                    size_old,
                    new_rect.size(),
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
                _, qwidget = win._split_interface_and_frontend()
                if qwidget is self._widget:
                    return (i_tab, i_win), main
        raise RuntimeError("Could not find the sub-window in the main window.")

    def dragEnterEvent(self, a0: QtGui.QDragEnterEvent | None) -> None:
        if a0 is None:
            return None
        if model := _drag.get_dragging_model():
            if self._my_wrapper()._is_drop_accepted(model):
                a0.accept()
                return None
        a0.ignore()
        return None

    def dropEvent(self, a0: QtGui.QDropEvent | None) -> None:
        if a0 is None:
            return None
        if model := _drag.drop():
            # user defined drop event
            self_wrapper = self._my_wrapper()
            if isinstance(src := a0.source(), QSubWindow):
                source = src._my_wrapper()
            else:
                source = None
            if self_wrapper.widget is src:  # same widget
                a0.ignore()
                _LOGGER.info("dropping to the same widget, ignore it")
                return None

            if self_wrapper._process_drop_event(model, source):
                a0.accept()
                return None
        a0.ignore()
        a0.setDropAction(Qt.DropAction.IgnoreAction)
        return None


class QTitleBarToolButton(QtW.QToolButton):
    """Tool button for the title bar of the sub-window."""

    def __init__(
        self,
        icon_id: TitleIconId,
        color: str,
        tooltip: str,
        callback: Callable[[], None],
    ):
        super().__init__()
        self._icon_id = icon_id
        self._current_icon_color = color
        self.setToolTip(tooltip)
        self.clicked.connect(callback)
        self._update_icon_color(color)

    def _set_size(self, size: int):
        self.setFixedSize(size, size)
        self.setIconSize(QtCore.QSize(size - 1, size - 1))

    def _update_icon_color(self, color: str):
        self._current_icon_color = color
        self.setIcon(_icon_for_id(self._icon_id, color))


class QDummyToolButton(QtW.QWidget):
    """Invisible widget just for API compatibility."""

    def __init__(self):
        super().__init__()
        self.setVisible(False)

    def _set_size(self, size: int):
        self.setFixedSize(size, size)

    def _update_icon_color(self, color: str):
        """Do nothing."""


class QSubWindowTitleBar(QtW.QFrame):
    """The subwindow title bar widget."""

    def __init__(self, subwindow: QSubWindow, title: str):
        super().__init__()
        self._drag_position: QtCore.QPoint | None = None
        self._is_window_drag_mode: bool = False
        self._is_double_clicking: bool = False
        self._resize_position: QtCore.QPoint | None = None
        self._subwindow = subwindow

        self.setFrameShape(QtW.QFrame.Shape.StyledPanel)
        self.setFrameShadow(QtW.QFrame.Shadow.Raised)
        self.setMinimumWidth(100)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

        self._window_menu_btn = QTitleBarToolButton(
            icon_id=TitleIconId.WINDOW_MENU,
            color="black",
            tooltip="Menu for this window",
            callback=self._show_window_menu,
        )
        if self._get_model_type() is not None:
            self._model_menu_btn = QTitleBarToolButton(
                icon_id=TitleIconId.MODEL_MENU,
                color="black",
                tooltip="Menu specific to the model",
                callback=self._show_model_menu,
            )
            # action hint button
            self._action_hint_btn = QTitleBarToolButton(
                icon_id=TitleIconId.ACTION_HINT,
                color="black",
                tooltip="Click to see available action hints",
                callback=self._show_action_hints,
            )
        else:
            self._model_menu_btn = QDummyToolButton()
            self._action_hint_btn = QDummyToolButton()

        self._index_label = QtW.QLabel()
        self._index_label.setObjectName("indexLabel")
        self._index_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
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
            icon_id=TitleIconId.MIN,
            color="black",
            tooltip="Minimize this window",
            callback=self._minimize,
        )
        self._toggle_size_btn = QTitleBarToolButton(
            icon_id=TitleIconId.MAX,
            color="black",
            tooltip="Toggle the size of this window",
            callback=self._toggle_size,
        )
        self._close_btn = QTitleBarToolButton(
            icon_id=TitleIconId.CLOSE,
            color="black",
            tooltip="Close this window",
            callback=self._close,
        )

        layout = QtW.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(1)
        layout.addWidget(self._window_menu_btn)
        layout.addWidget(self._model_menu_btn)
        layout.addWidget(self._action_hint_btn)
        layout.addWidget(self._index_label)
        layout.addWidget(self._title_label)
        layout.addWidget(self._minimize_btn, alignment=Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self._toggle_size_btn, alignment=Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self._close_btn, alignment=Qt.AlignmentFlag.AlignRight)

        self.setProperty("isCurrent", False)
        self.setAcceptDrops(True)
        self._bar_size = 18
        self._set_bar_size(self._bar_size)

    def _get_model_type(self) -> str | None:
        interf = self._subwindow._my_wrapper().widget
        if hasattr(interf, "model_type"):
            try:
                return interf.model_type()
            except Exception:
                return None
        elif hasattr(interf, "__himena_model_type__"):
            return interf.__himena_model_type__
        return None

    def _set_visible(self, visible: bool):
        if visible:
            self._set_bar_size(self._bar_size)
        else:
            self._set_bar_size(0)

    def _set_bar_size(self, height: int):
        self.setFixedHeight(height)
        self._index_label.setFixedHeight(height)
        self._title_label.setFixedHeight(height)
        if height > 1:
            self._window_menu_btn._set_size(height - 1)
            self._model_menu_btn._set_size(height - 1)
            self._action_hint_btn._set_size(height - 1)
            self._minimize_btn._set_size(height - 1)
            self._toggle_size_btn._set_size(height - 1)
            self._close_btn._set_size(height - 1)

    def _set_icon_color(self, color):
        for toolbtn in (
            self._window_menu_btn,
            self._model_menu_btn,
            self._action_hint_btn,
            self._minimize_btn,
            self._toggle_size_btn,
            self._close_btn,
        ):
            toolbtn._update_icon_color(color)

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
        """Make the tooltip for the title bar"""
        qwin = self._subwindow
        attrs: list[str] = [f"<b>Title</b>: {self._title_label.text()}"]
        if _model_type := self._get_model_type():
            attrs.append(f"<b>Type</b>: {_model_type}")
        attrs.append(
            f"<b>Widget</b>: {get_display_name(qwin._widget.__class__, sep=' ')}"
        )
        sub = qwin._my_wrapper()
        attrs.append(f"<b>Save behavior</b>: {sub.save_behavior!r}")
        tooltip = "<br>".join(attrs)
        return tooltip

    def event(self, a0: QtCore.QEvent) -> bool:
        if a0.type() == QtCore.QEvent.Type.ToolTip:
            a0 = cast(QtGui.QHelpEvent, a0)
            QtW.QToolTip.showText(a0.globalPos(), self._make_tooltip(), self)
            return True
        return super().event(a0)

    # drag events for moving the window
    def mousePressEvent(self, event: QtGui.QMouseEvent):
        self._is_window_drag_mode = False
        if self._is_double_clicking:
            return super().mousePressEvent(event)
        _subwin = self._subwindow
        _left_btn = event.buttons() & Qt.MouseButton.LeftButton
        _middle_btn = event.buttons() & Qt.MouseButton.MiddleButton
        _ctrl_mod = event.modifiers() & Qt.KeyboardModifier.ControlModifier
        if (_left_btn and _ctrl_mod) or _middle_btn:
            # start dragging subwindow
            self._is_window_drag_mode = True
            drag = self._make_subwindow_drag()
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
        if event.buttons() == Qt.MouseButton.NoButton:
            self._drag_position = None
        elif (
            event.buttons() == Qt.MouseButton.LeftButton
            and self._drag_position is not None
            and _subwin._resize_state is ResizeState.NONE
            and not self._is_window_drag_mode
        ):
            g = _subwin.geometry()
            main_qsize = _subwin._qt_mdiarea().size()
            wrapper = _subwin._my_wrapper()
            if _subwin._window_state == WindowState.MAX:
                # change to normal without moving
                self._toggle_size_btn.setIcon(
                    _icon_for_id(TitleIconId.MAX, self._subwindow._current_icon_color)
                )
                _subwin._widget.setVisible(True)
                _subwin._window_state = WindowState.NORMAL
                # restore the last size
                _last_geo = _subwin._last_geometry
                _next_rect = WindowRect(
                    event.pos().x() - _last_geo.width() // 2,
                    event.pos().y() - self.height() // 2,
                    _last_geo.width(),
                    _last_geo.height(),
                )
                self._store_drag_position(event.globalPos())
            else:
                # drag the subwindow
                new_pos = event.globalPos() - self._drag_position
                offset = self.height() - 4
                if new_pos.y() < -offset:
                    new_pos.setY(-offset)
                _next_rect = wrapper.rect.move_top_left(new_pos.x(), new_pos.y())

            # update window anchor
            wrapper.rect = _next_rect
            wrapper.anchor = wrapper.anchor.update_for_window_rect(
                (main_qsize.width(), main_qsize.height()),
                WindowRect.from_tuple(g.left(), g.top(), g.width(), g.height()),
            )
        return super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent):
        self._is_window_drag_mode = False
        self._is_double_clicking = False
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_position = None
            self._fix_position()
        elif event.button() == Qt.MouseButton.RightButton:
            # context menu
            if (event.pos() - self._drag_position).manhattanLength() < 10:
                context_menu = self._prep_window_menu()
                context_menu.exec(event.globalPos())
        return super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event: QtGui.QMouseEvent):
        self._is_double_clicking = True
        if event.buttons() & Qt.MouseButton.LeftButton:
            self._toggle_size()
        return super().mouseDoubleClickEvent(event)

    def wheelEvent(self, event: QtGui.QWheelEvent):
        if event.modifiers() == Qt.KeyboardModifier.NoModifier:
            self._wheel_event(event.angleDelta().y())
        return super().wheelEvent(event)

    def _wheel_event(self, dy: int):
        subwin = self._subwindow
        i_tab, i_win = subwin._find_me()
        main = get_main_window(subwin)
        sub = main.tabs[i_tab][i_win]
        size_old = sub.size
        if dy > 0:
            rect_new = sub.rect.resize_relative(1.1, 1.1)
        else:
            rect_new = sub.rect.resize_relative(1 / 1.1, 1 / 1.1)
        inst = main._instructions.updated(animate=False)
        sub._set_rect(rect_new, inst)
        size_new = rect_new.size()
        return _checker.call_widget_resized_callback(
            subwin._my_wrapper().widget, size_old, size_new
        )

    def _make_subwindow_drag(self):
        _subwin = self._subwindow
        drag = QtGui.QDrag(_subwin)
        drag.destroyed.connect(_drag.clear)
        mime_data = QtCore.QMimeData()
        _wrapper = self._subwindow._my_wrapper()
        if isinstance(
            _meth := _wrapper._widget_workflow.last(),
            LocalReaderMethod,
        ):
            if isinstance(_meth.path, Path):
                mime_data.setUrls([QtCore.QUrl(_meth.path.as_uri())])
            elif isinstance(_meth.path, list):
                mime_data.setUrls([QtCore.QUrl(fp.as_uri()) for fp in _meth.path])
        drag.setMimeData(mime_data)
        if _wrapper.supports_to_model:
            model = DragDataModel(
                getter=_wrapper.to_model,
                type=_wrapper.model_type(),
            )
            _drag.drag(model)
        drag.setPixmap(_subwin._pixmap_resized(QtCore.QSize(150, 150)))
        return drag

    def dragEnterEvent(self, a0: QtGui.QDragEnterEvent | None) -> None:
        return self._subwindow.dragEnterEvent(a0)

    def dropEvent(self, a0: QtGui.QDropEvent | None) -> None:
        return self._subwindow.dropEvent(a0)

    def enterEvent(self, event):
        ui = get_main_window(self)
        ui.set_status_tip("`Ctrl+LeftButton` or `MiddleButton` to drag the window")
        return super().enterEvent(event)

    def leaveEvent(self, a0):
        try:
            main = get_main_window(self)
        except ValueError:
            pass
        else:
            main.set_status_tip("")
        return super().leaveEvent(a0)

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
        context_menu = self._prep_model_menu()
        return self._exec_menu_at_button(context_menu, self._model_menu_btn)

    def _show_action_hints(self):
        context_menu = self._prep_action_hints_menu()
        if len(context_menu.actions()) == 0:
            action = context_menu.addAction("No action hints available", lambda: None)
            action.setEnabled(False)
        return self._exec_menu_at_button(context_menu, self._action_hint_btn)

    def _prep_window_menu(self) -> QtW.QMenu:
        main = get_main_window(self)
        app = main._model_app

        context_menu = build_qmodel_menu(MenuId.WINDOW, app=app.name, parent=self)
        ctx = main._ctx_keys
        ctx._update(main)
        context_menu.update_from_context(ctx.dict())
        return context_menu

    def _prep_model_menu(self) -> QtW.QMenu:
        model_type = self._get_model_type()
        if model_type is None:
            return None
        ui = get_main_window(self)
        model_subtypes = model_type.split(".")
        supertype_menus: list[QtW.QMenu] = []
        _id = f"/model_menu:{model_type}"

        context_menu = build_qmodel_menu(_id, app=ui.model_app.name, parent=self)
        ctx = ui._ctx_keys
        ctx._update(ui)
        ctx_dict = ctx.dict()
        open_in_actions: list[QCommandRuleAction] = []
        _n_enabled = 0
        for i in range(1, len(model_subtypes) + 1):
            _typ = ".".join(model_subtypes[:i])
            _id_open_in = f"/open-in/{_typ}"
            for menu_group in ui.model_app.menus.iter_menu_groups(_id_open_in):
                for menu_or_submenu in menu_group:
                    if isinstance(menu_or_submenu, MenuItem):
                        action = QCommandRuleAction(
                            menu_or_submenu.command, ui.model_app.name, self
                        )
                        is_enabled = menu_or_submenu.command.enablement.eval(ctx_dict)
                        _n_enabled += int(is_enabled)
                        action.setEnabled(is_enabled)
                        open_in_actions.append(action)
        if open_in_actions and _n_enabled > 0:
            open_in_menu = QtW.QMenu()
            open_in_menu.setParent(context_menu, open_in_menu.windowFlags())
            open_in_menu.setTitle("Open in ...")
            actions = context_menu.actions()
            if len(actions) == 0:
                context_menu.addMenu(open_in_menu)
            else:
                context_menu.insertMenu(actions[0], open_in_menu)
            for action in open_in_actions:
                open_in_menu.addAction(action)

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
        context_menu.update_from_context(ctx_dict)
        return context_menu

    def _prep_action_hints_menu(self) -> QtW.QMenu:
        ui = get_main_window(self)
        model_type = self._get_model_type()
        if model_type is None:
            return QtW.QMenu()
        subwin = self._subwindow._my_wrapper()
        last_step = subwin._widget_workflow.last()
        if last_step is None:
            return QtW.QMenu()
        menu = QtW.QMenu()
        for sug in ui.action_hint_registry.iter_suggestion(model_type, last_step):
            menu.addAction(sug.get_title(ui), sug.make_executor(ui, last_step))
        menu.setParent(self, menu.windowFlags())
        return menu

    def _show_window_menu(self):
        context_menu = self._prep_window_menu()
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
        painter.drawRect(pixmap.rect().adjusted(0, 0, -1, -1))
        painter.end()
    return pixmap


CURSOR_SHAPE_MAP = {
    ResizeState.TOP: Qt.CursorShape.SizeVerCursor,
    ResizeState.BOTTOM: Qt.CursorShape.SizeVerCursor,
    ResizeState.LEFT: Qt.CursorShape.SizeHorCursor,
    ResizeState.RIGHT: Qt.CursorShape.SizeHorCursor,
    ResizeState.TOP_LEFT: Qt.CursorShape.SizeFDiagCursor,
    ResizeState.TOP_RIGHT: Qt.CursorShape.SizeBDiagCursor,
    ResizeState.BOTTOM_LEFT: Qt.CursorShape.SizeBDiagCursor,
    ResizeState.BOTTOM_RIGHT: Qt.CursorShape.SizeFDiagCursor,
    ResizeState.NONE: Qt.CursorShape.ArrowCursor,
}


def get_subwindow(widget: QtW.QWidget) -> QSubWindow:
    window = widget.parentWidget().parentWidget().parentWidget()
    if not isinstance(window, QSubWindow):
        raise ValueError(f"Widget {widget!r} is not in a sub-window.")
    return window
