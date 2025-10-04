from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Iterable, Iterator, Literal
import weakref
from qtpy import QtWidgets as QtW
from qtpy import QtCore, QtGui
from qtpy.QtCore import Qt
from himena.plugins._checker import validate_protocol
from himena.standards.model_meta import TableMeta
from himena.qt._qfinderwidget import QTableFinderWidget
from himena.utils.misc import is_absolute_file_path_string, is_url_string
from ._selection_model import SelectionModel, Index
from ._header import QVerticalHeaderView, QHorizontalHeaderView

if TYPE_CHECKING:
    from himena.widgets import MainWindow


class QItemDelegate(QtW.QStyledItemDelegate):
    def __init__(self, parent: QtCore.QObject | None = None) -> None:
        super().__init__(parent)
        self._current_editor_ref: Callable[[], QTableEditor | None] = lambda: None

    def createEditor(
        self,
        parent: QtW.QWidget,
        option,
        index: QtCore.QModelIndex,
    ) -> QTableEditor:
        editor = QTableEditor(parent)
        self._current_editor_ref = weakref.ref(editor)
        editor.setText(index.data())
        return editor

    def paint(
        self,
        painter: QtGui.QPainter,
        option: QtW.QStyleOptionViewItem,
        index: QtCore.QModelIndex,
    ):
        if (
            (option.state & QtW.QStyle.StateFlag.State_MouseOver)
            and isinstance(text := index.data(), str)
            and (is_absolute_file_path_string(text) or is_url_string(text))
        ):
            option.font.setUnderline(True)
        super().paint(painter, option, index)
        if option.state & QtW.QStyle.StateFlag.State_MouseOver:
            painter.setPen(QtGui.QPen(self.parent()._hover_color, 2))
            painter.drawRect(option.rect.adjusted(1, 1, -1, -1))

    def initStyleOption(
        self, option: QtW.QStyleOptionViewItem, index: QtCore.QModelIndex
    ):
        super().initStyleOption(option, index)
        if option.state & QtW.QStyle.StateFlag.State_HasFocus:
            option.state = option.state & ~QtW.QStyle.StateFlag.State_HasFocus

    # fmt: off
    if TYPE_CHECKING:
        def parent(self) -> QTableBase: ...
    # fmt: on


class QTableBase(QtW.QTableView):
    """The base class for high-performance table widgets."""

    selection_changed = QtCore.Signal(list)
    current_index_changed = QtCore.Signal(tuple)

    def __init__(self, ui: MainWindow, parent: QtW.QWidget | None = None) -> None:
        super().__init__(parent)
        self._ui = ui
        self._vertical_header = QVerticalHeaderView(self)
        self._horizontal_header = QHorizontalHeaderView(self)
        self.setVerticalHeader(self._vertical_header)
        self.setHorizontalHeader(self._horizontal_header)
        self.setMouseTracking(True)

        self.horizontalHeader().setFixedHeight(18)
        self.verticalHeader().setDefaultSectionSize(22)
        self.horizontalHeader().setDefaultSectionSize(75)
        self.setItemDelegate(QItemDelegate(self))
        self._finder_widget: QTableFinderWidget | None = None

        # scroll by pixel
        self.setVerticalScrollMode(QtW.QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.setHorizontalScrollMode(QtW.QAbstractItemView.ScrollMode.ScrollPerPixel)
        # scroll bar policy
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        self.setSelectionMode(QtW.QAbstractItemView.SelectionMode.ExtendedSelection)

        self.setWordWrap(False)  # this disables eliding float text
        self.setSelectionMode(QtW.QAbstractItemView.SelectionMode.NoSelection)
        self._selection_model = SelectionModel(
            lambda: self.model().rowCount(),
            lambda: self.model().columnCount(),
        )
        self._selection_model.moving.connect(self._on_moving)
        self._selection_model.moved.connect(self._on_moved)
        self._selection_color = QtGui.QColor("#777777")
        self._hover_color = QtGui.QColor(self._selection_color)
        self._current_color = QtGui.QColor("#A7A7A7")
        self._mouse_track = MouseTrack()
        self._modified_override: bool | None = None

    @property
    def selection_model(self) -> SelectionModel:
        """The custom selection model."""
        return self._selection_model

    @QtCore.Property(QtGui.QColor)
    def selectionColor(self):
        return self._selection_color

    @selectionColor.setter
    def selectionColor(self, color: QtGui.QColor):
        self._selection_color = color
        self._hover_color = QtGui.QColor(color)
        self._hover_color.setAlpha(128)

    def data_shape(self) -> tuple[int, int]:
        """Shape of the data, not the table itself."""
        model = self.model()
        return model.rowCount(), model.columnCount()

    def selectAll(self):
        return self.select_all()

    def select_all(self):
        """Override selectAll slot to update custom selections."""
        nr, nc = self.data_shape()
        if nr * nc > 0:
            self.set_selections([(slice(0, nr), slice(0, nc))])

    def set_selections(self, selections: list[tuple[slice, slice]]) -> None:
        """Set current selections."""
        self._selection_model.set_ranges(selections)
        self._update_all()

    @validate_protocol
    def size_hint(self) -> tuple[int, int]:
        return 400, 300

    @validate_protocol
    def is_editable(self) -> bool:
        return self.editTriggers() != QtW.QAbstractItemView.EditTrigger.NoEditTriggers

    @validate_protocol
    def set_editable(self, editable: bool):
        self.setEditTriggers(Editability.TRUE if editable else Editability.FALSE)

    def _find_string(self):
        if self._finder_widget is None:
            self._finder_widget = QTableFinderWidget(self)
        self._finder_widget.show()
        self._align_finder()

    def resizeEvent(self, event):
        if self._finder_widget is not None:
            self._align_finder()
        super().resizeEvent(event)

    def _align_finder(self):
        if fd := self._finder_widget:
            vbar = self.verticalScrollBar()
            if vbar.isVisible():
                fd.move(self.width() - fd.width() - vbar.width() - 3, 5)
            else:
                fd.move(self.width() - fd.width() - 3, 5)

    def _get_selections(self) -> list[tuple[tuple[int, int], tuple[int, int]]]:
        return [
            ((r.start, r.stop), (c.start, c.stop)) for r, c in self._selection_model
        ]

    def _prep_table_meta(self, cls=TableMeta) -> TableMeta:
        index = self._selection_model.current_index
        return cls(
            current_position=(index.row, index.column),
            selections=self._get_selections(),
        )

    def itemDelegate(self) -> QItemDelegate:
        return super().itemDelegate()

    def _update_rect(self, rect: QtCore.QRect) -> None:
        rect.adjust(-2, -2, 2, 2)
        return self.viewport().update(rect)

    def _update_all(self, rect: QtCore.QRect | None = None) -> None:
        """repaint the table and the headers."""
        if rect is None:
            self.viewport().update()
        else:
            rect.adjust(-2, -2, 2, 2)
            self.viewport().update(rect)
        self.horizontalHeader().viewport().update()
        self.verticalHeader().viewport().update()

    def _range_rect(self, rng: tuple[slice, slice]) -> QtCore.QRect:
        rsel, csel = rng
        model = self.model()
        rect = self.visualRect(model.index(rsel.start, csel.start))
        rect |= self.visualRect(model.index(rsel.stop - 1, csel.stop - 1))
        return rect

    def _on_moving(self, src: Index, dst: Index) -> None:
        if not self._selection_model.is_jumping():
            # clear all the multi-selections
            for sel in self._selection_model:
                self._update_rect(self._range_rect(sel))

        else:
            if len(self._selection_model) > 1:
                self._update_rect(self._range_rect(self._selection_model[-2]))

        if self._selection_model.is_moving_to_edge():
            if len(self._selection_model) > 0:
                self._update_rect(self._range_rect(self._selection_model[-1]))

    def _on_moved(self, src: Index, dst: Index) -> None:
        """Update the view."""
        model = self.model()
        index_src = model.index(*src.as_uint())
        index_dst = model.index(*dst.as_uint())
        if dst >= (0, 0):
            if self.hasFocus():
                self.scrollTo(index_dst)
        elif dst.row < 0:
            v_value = self.verticalScrollBar().value()
            self.scrollTo(model.index(0, dst.column))
            self.verticalScrollBar().setValue(v_value)
        elif dst.column < 0:
            h_value = self.horizontalScrollBar().value()
            self.scrollTo(model.index(dst.row, 0))
            self.horizontalScrollBar().setValue(h_value)

        # rect is the region that needs to be updated
        rect: QtCore.QRect = self.visualRect(index_dst)
        if not self._selection_model.is_jumping():
            rect |= self.visualRect(index_src)
        if sel := self._selection_model.current_range:
            rect |= self._range_rect(sel)
        if start := self._selection_model.start:
            rect |= self.visualRect(model.index(*start))

        if src.row < 0 or dst.row < 0:
            rect.setBottom(999999)
        if src.column < 0 or dst.column < 0:
            rect.setRight(999999)

        self._update_all(rect)
        if dst.row >= 0 and dst.column >= 0:
            self.setCurrentIndex(index_dst)
        self.selection_changed.emit(self._get_selections())
        self.current_index_changed.emit(dst.as_uint())

    def keyPressEvent(self, e):
        _mod = e.modifiers()
        _key = e.key()
        has_ctrl = _mod & Qt.KeyboardModifier.ControlModifier
        has_shift = _mod & Qt.KeyboardModifier.ShiftModifier
        self._selection_model.set_shift(has_shift)
        self._selection_model.set_ctrl(has_ctrl)
        if has_ctrl:
            nr, nc = self.data_shape()
            if _key == Qt.Key.Key_Up:
                dr, dc = -99999999, 0
            elif _key == Qt.Key.Key_Down:
                dr, dc = 99999999, 0
            elif _key == Qt.Key.Key_Left:
                dr, dc = 0, -99999999
            elif _key == Qt.Key.Key_Right:
                dr, dc = 0, 99999999
            elif _key == Qt.Key.Key_A:
                self.select_all()
                return None
            else:
                return super().keyPressEvent(e)
            self._selection_model.move_limited(dr, dc, nr, nc)
            return None
        elif _mod == Qt.KeyboardModifier.NoModifier or has_shift:
            if _key == Qt.Key.Key_Up:
                dr, dc = -1, 0
            elif _key == Qt.Key.Key_Down:
                dr, dc = 1, 0
            elif _key == Qt.Key.Key_Left:
                dr, dc = 0, -1
            elif _key == Qt.Key.Key_Right:
                dr, dc = 0, 1
            elif _key == Qt.Key.Key_PageUp:
                dr, dc = -10, 0
            elif _key == Qt.Key.Key_PageDown:
                dr, dc = 10, 0
            elif _key == Qt.Key.Key_Home:
                dr, dc = 0, -10
            elif _key == Qt.Key.Key_End:
                dr, dc = 0, 10
            else:
                return super().keyPressEvent(e)
            self._selection_model.move(dr, dc, allow_header=True)
            return None
        return super().keyPressEvent(e)

    def keyReleaseEvent(self, a0: QtGui.QKeyEvent) -> None:
        has_ctrl = a0.modifiers() & Qt.KeyboardModifier.ControlModifier
        has_shift = a0.modifiers() & Qt.KeyboardModifier.ShiftModifier
        self._selection_model.set_ctrl(has_ctrl)
        self._selection_model.set_shift(
            has_shift or self._mouse_track.last_click_pos is not None
        )
        return super().keyReleaseEvent(a0)

    def mousePressEvent(self, e: QtGui.QMouseEvent) -> None:
        """Register clicked position"""
        self._mouse_press_event(e.pos(), e.button())
        return super().mousePressEvent(e)

    def _mouse_press_event(self, pos: QtCore.QPoint, button: int) -> None:
        """Handle mouse press event."""
        _selection_model = self._selection_model
        self._mouse_track.was_right_dragging = False
        if button == Qt.MouseButton.LeftButton:
            index = self.indexAt(pos)
            if index.isValid():
                r, c = index.row(), index.column()
                _selection_model.jump_to(r, c)
            else:
                self.closePersistentEditor(index)
            self._mouse_track.press_at(pos, "left")
        elif button == Qt.MouseButton.RightButton:
            return self._mouse_track.press_at(pos, "right")
        elif button == Qt.MouseButton.MiddleButton:
            return self._mouse_track.press_at(pos, "middle")
        _selection_model.set_shift(True)

    def mouseMoveEvent(self, e: QtGui.QMouseEvent) -> None:
        """Scroll table plane when mouse is moved with right click."""
        ctrl_down = bool(e.modifiers() & Qt.KeyboardModifier.ControlModifier)
        self._mouse_move_event(e.pos(), ctrl_down)
        return super().mouseMoveEvent(e)

    def _mouse_move_event(self, pos: QtCore.QPoint, ctrl_down: bool) -> None:
        """Handle mouse move event."""
        if self._mouse_track.last_button is None:
            self._set_status_tip_for_text(self._text_for_pos(pos), ctrl_down)
        elif self._mouse_track.last_button in ("right", "middle"):
            self._process_table_drag(pos)
        elif self._mouse_track.last_button == "left":
            index = self.indexAt(pos)
            if index.isValid():
                r, c = index.row(), index.column()
                if self._selection_model.current_index != (r, c):
                    self._selection_model.move_to(r, c)

    def mouseReleaseEvent(self, e: QtGui.QMouseEvent) -> None:
        """Delete last position."""
        if self._mouse_track.last_button == "right":
            index = self.indexAt(e.pos())
            if not self.selection_model.contains((index.row(), index.column())):
                self._selection_model.jump_to(index.row(), index.column())
            if self._mouse_track.is_close_to(e.pos()):  # right click
                menu = self._make_context_menu()
                if menu is not None:
                    menu.exec(self.viewport().mapToGlobal(e.pos()))
        elif self._mouse_track.last_button == "left":
            if (
                self._mouse_track.is_close_to(e.pos())
                and (e.modifiers() & Qt.KeyboardModifier.ControlModifier)
                and (text := self._text_for_pos(e.pos()))
            ):
                if is_absolute_file_path_string(text):
                    self._ui.read_file(text)
                elif is_url_string(text):
                    QtGui.QDesktopServices.openUrl(QtCore.QUrl(text))  # open URL

        self._mouse_track.last_click_pos = None
        self._mouse_track.last_drag_pos = None
        self._mouse_track.last_button = None
        self._selection_model.set_shift(
            e.modifiers() & Qt.KeyboardModifier.ShiftModifier
        )
        self._mouse_track.was_right_dragging = False
        return super().mouseReleaseEvent(e)

    def _set_status_tip_for_text(self, text_under_cursor: str | None, ctrl_down: bool):
        if text_under_cursor:
            if ctrl_down:
                self.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
            if is_absolute_file_path_string(text_under_cursor):
                status_tip = "Ctrl+Click to open file in this application"
            elif is_url_string(text_under_cursor):
                status_tip = "Ctrl+Click to open link in the default browser"
            else:
                status_tip = ""
                self.setCursor(QtCore.Qt.CursorShape.ArrowCursor)
            self._ui.set_status_tip(status_tip, 2.6)
        else:
            self.setCursor(QtCore.Qt.CursorShape.ArrowCursor)
            self._ui.set_status_tip("")

    def _process_table_drag(self, pos: QtCore.QPoint) -> None:
        assert self._mouse_track.last_drag_pos is not None
        dy = pos.y() - self._mouse_track.last_drag_pos.y()
        dx = pos.x() - self._mouse_track.last_drag_pos.x()
        self.verticalScrollBar().setValue(self.verticalScrollBar().value() - dy)
        self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - dx)
        self._mouse_track.last_drag_pos = pos
        self._mouse_track.was_right_dragging = True

    def _text_for_pos(self, pos: QtCore.QPoint) -> str | None:
        index = self.indexAt(pos)
        if index.isValid():
            text = index.data()
            if isinstance(text, str):
                return text

    def _make_context_menu(self) -> QtW.QMenu | None:
        """Overwrite to provide a context menu."""
        return None

    def paintEvent(self, event: QtGui.QPaintEvent):
        """Paint table and the selection."""
        super().paintEvent(event)
        focused = int(self.hasFocus())
        nsel = len(self._selection_model)
        painter = QtGui.QPainter(self.viewport())

        # draw selections
        s_color = self._selection_color
        for i, rect in enumerate(self._rect_from_ranges(self._selection_model._ranges)):
            if nsel == i + 1:
                pen = QtGui.QPen(s_color, 2 + focused)
            else:
                pen = QtGui.QPen(s_color, 2)
            painter.setPen(pen)
            painter.drawRect(rect)

        # current index
        idx = self._selection_model.current_index
        if idx >= (0, 0) and (_model := self.model()):
            rect_cursor = self.visualRect(_model.index(*idx))
            rect_cursor.adjust(1, 1, -1, -1)
            pen = QtGui.QPen(self._current_color, 2)
            painter.setPen(pen)
            painter.drawRect(rect_cursor)
        painter.end()

    def _rect_from_ranges(
        self,
        ranges: Iterable[tuple[slice, slice]],
    ) -> Iterator[QtCore.QRect]:
        """Convert range models into rectangles."""
        model = self.model()
        for rr, cc in ranges:
            if rr.start is None:
                rstart = 0
            else:
                rstart = rr.start
            if cc.start is None:
                cstart = 0
            else:
                cstart = cc.start
            top_left = model.index(rstart, cstart)

            if rr.stop is None:
                rstop = model.rowCount()
            else:
                rstop = rr.stop
            if cc.stop is None:
                cstop = model.columnCount()
            else:
                cstop = cc.stop
            bottom_right = model.index(rstop - 1, cstop - 1)
            rect = self.visualRect(top_left) | self.visualRect(bottom_right)
            yield rect


class QTableEditor(QtW.QLineEdit):
    """Custom cell editor that can smoothly move the focus to the next cell."""

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        """Handle key press events."""
        pos = self.cursorPosition()
        nchar = len(self.text())
        if event.key() == Qt.Key.Key_Left and pos == 0:
            self.parentWidget().setFocus()
            self.parentWidget().keyPressEvent(event)
            return None
        elif event.key() == Qt.Key.Key_Right and pos == nchar:
            if self.selectionLength() > 0:
                # just after entering the editor, all the text is selected and the
                # cursor is at the end. In this case, user is probably trying to
                # deselect the text, so we need to move the cursor to the end instead of
                # moving to the next cell.
                self.setCursorPosition(nchar)
            else:
                self.parentWidget().setFocus()
                self.parentWidget().keyPressEvent(event)
            return None
        return super().keyPressEvent(event)


class MouseTrack:
    """Info about the mouse position and button state"""

    def __init__(self):
        self.last_click_pos: QtCore.QPoint | None = None
        self.last_drag_pos: QtCore.QPoint | None = None
        self.was_right_dragging: bool = False
        self.last_button: Literal["left", "middle", "right"] | None = None

    def press_at(self, pos: QtCore.QPoint, button: Literal["left", "middle", "right"]):
        self.last_click_pos = pos
        self.last_drag_pos = pos
        self.last_button = button

    def is_close_to(self, pos: QtCore.QPoint, tol=3) -> bool:
        if self.last_click_pos is None:
            return False
        return (self.last_click_pos - pos).manhattanLength() <= tol


class Editability:
    TRUE = (
        QtW.QAbstractItemView.EditTrigger.DoubleClicked
        | QtW.QAbstractItemView.EditTrigger.EditKeyPressed
    )
    FALSE = QtW.QAbstractItemView.EditTrigger.NoEditTriggers


FLAGS = (
    Qt.ItemFlag.ItemIsEnabled
    | Qt.ItemFlag.ItemIsSelectable
    | Qt.ItemFlag.ItemIsEditable
)


def parse_string(value: str, dtype_kind: str) -> Any:
    if dtype_kind in "iu":
        return int(value)
    if dtype_kind == "f":
        return float(value)
    if dtype_kind == "b":
        return bool(value)
    if dtype_kind == "c":
        return complex(value)
    if dtype_kind == "S":
        return value.encode()
    return value
