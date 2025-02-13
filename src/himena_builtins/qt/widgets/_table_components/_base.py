from __future__ import annotations

from typing import TYPE_CHECKING, Any, Iterable, Iterator, Literal
from qtpy import QtWidgets as QtW
from qtpy import QtCore, QtGui
from qtpy.QtCore import Qt
from himena.plugins._checker import validate_protocol
from himena.standards.model_meta import TableMeta
from himena.qt._qfinderwidget import QTableFinderWidget
from ._selection_model import SelectionModel, Index
from ._header import QVerticalHeaderView, QHorizontalHeaderView

if TYPE_CHECKING:
    from PyQt6 import QtWidgets as QtW


class QItemDelegate(QtW.QStyledItemDelegate):
    def __init__(self, parent: QtCore.QObject | None = None) -> None:
        super().__init__(parent)
        self._current_editor: QTableEditor | None = None

    def createEditor(
        self,
        parent: QtW.QWidget,
        option,
        index: QtCore.QModelIndex,
    ) -> QTableEditor:
        editor = QTableEditor(parent)
        self._current_editor = editor
        editor.setText(index.data())
        return editor

    def paint(
        self,
        painter: QtGui.QPainter,
        option: QtW.QStyleOptionViewItem,
        index: QtCore.QModelIndex,
    ):
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

    def __init__(self, parent: QtW.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setVerticalHeader(QVerticalHeaderView(self))
        self.setHorizontalHeader(QHorizontalHeaderView(self))

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
        return None

    def set_selections(self, selections: list[tuple[slice, slice]]) -> None:
        """Set current selections."""
        self._selection_model.set_ranges(selections)
        self._update_all()
        return None

    @validate_protocol
    def size_hint(self) -> tuple[int, int]:
        return 400, 300

    @validate_protocol
    def is_editable(self) -> bool:
        return self.editTriggers() != QtW.QAbstractItemView.EditTrigger.NoEditTriggers

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
        return None

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

        return None

    def _on_moved(self, src: Index, dst: Index) -> None:
        """Update the view."""
        model = self.model()
        index_src = model.index(*src.as_uint())
        index_dst = model.index(*dst.as_uint())
        if dst >= (0, 0):
            if self.hasFocus():
                self.scrollTo(index_dst)
        elif dst.row < 0:
            self.scrollTo(model.index(0, dst.column))
        elif dst.column < 0:
            self.scrollTo(model.index(dst.row, 0))

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
        return None

    def edit(self, index: QtCore.QModelIndex, *args) -> bool:
        """Edit at the current index of custom selection model."""
        self._selection_model.current_index = (index.row(), index.column())
        return super().edit(index, *args)

    def keyPressEvent(self, e):
        _mod = e.modifiers()
        _key = e.key()
        self._selection_model.set_shift(_mod & Qt.KeyboardModifier.ShiftModifier)
        if _mod & Qt.KeyboardModifier.ControlModifier:
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
        elif (
            _mod == Qt.KeyboardModifier.NoModifier
            or _mod & Qt.KeyboardModifier.ShiftModifier
        ):
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
                dr, dc = -10, 0
            elif _key == Qt.Key.Key_End:
                dr, dc = 10, 0
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
            has_shift or self._mouse_track.last_rightclick_pos is not None
        )
        return super().keyReleaseEvent(a0)

    def mousePressEvent(self, e: QtGui.QMouseEvent) -> None:
        """Register clicked position"""
        # initialize just in case

        _selection_model = self._selection_model
        _selection_model.set_ctrl(e.modifiers() & Qt.KeyboardModifier.ControlModifier)
        self._mouse_track.last_rightclick_pos = e.pos()
        if e.button() == Qt.MouseButton.LeftButton:
            index = self.indexAt(e.pos())
            if index.isValid():
                r, c = index.row(), index.column()
                self._selection_model.jump_to(r, c)
            else:
                # TODO: if outside the table is clicked, close the editor
                pass
            self._mouse_track.last_button = "left"
        elif e.button() == Qt.MouseButton.RightButton:
            self._mouse_track.was_right_dragging = False
            self._mouse_track.last_button = "right"
            return
        _selection_model.set_shift(True)
        return super().mousePressEvent(e)

    def mouseMoveEvent(self, e: QtGui.QMouseEvent) -> None:
        """Scroll table plane when mouse is moved with right click."""
        if e.buttons() == Qt.MouseButton.NoButton:
            return None
        if self._mouse_track.last_button == "right":
            pos = e.pos()
            dy = pos.y() - self._mouse_track.last_rightclick_pos.y()
            dx = pos.x() - self._mouse_track.last_rightclick_pos.x()
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - dy)
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - dx)
            self._mouse_track.last_rightclick_pos = pos
            self._mouse_track.was_right_dragging = True
        else:
            index = self.indexAt(e.pos())
            if index.isValid():
                r, c = index.row(), index.column()
                if self._selection_model.current_index != (r, c):
                    self._selection_model.move_to(r, c)

        return None

    def mouseReleaseEvent(self, e: QtGui.QMouseEvent) -> None:
        """Delete last position."""
        if self._mouse_track.last_button == "right":
            index = self.indexAt(e.pos())
            if not self.selection_model.contains((index.row(), index.column())):
                self._selection_model.jump_to(index.row(), index.column())
            if self._mouse_track.last_rightclick_pos == e.pos():
                # right click
                menu = self._make_context_menu()
                if menu is not None:
                    menu.exec_(self.viewport().mapToGlobal(e.pos()))
        self._mouse_track.last_rightclick_pos = None
        self._mouse_track.last_button = None
        self._selection_model.set_shift(
            e.modifiers() & Qt.KeyboardModifier.ShiftModifier
        )
        self._mouse_track.was_right_dragging = False
        return super().mouseReleaseEvent(e)

    def _make_context_menu(self) -> QtW.QMenu | None:
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
        return None

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
            self.parentWidget().setFocus()
            self.parentWidget().keyPressEvent(event)
            return None
        return super().keyPressEvent(event)


class MouseTrack:
    """Info about the mouse position and button state"""

    def __init__(self):
        self.last_rightclick_pos: QtCore.QPoint | None = None
        self.was_right_dragging: bool = False
        self.last_button: Literal["left", "right"] | None = None


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
