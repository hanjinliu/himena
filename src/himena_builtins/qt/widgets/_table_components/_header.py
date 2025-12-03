from __future__ import annotations
from typing import TYPE_CHECKING, Iterator
import warnings
import weakref
from qtpy import QtWidgets as QtW, QtCore, QtGui
from qtpy.QtCore import Qt

from himena import StandardType
from himena.utils import proxy
from himena.qt import drag_command
from himena.data_wrappers import wrap_dataframe
from himena_builtins.qt.widgets._dragarea import QDraggableArea

if TYPE_CHECKING:
    from himena_builtins.qt.widgets._table_components import QTableBase
    from himena_builtins.qt.widgets.dataframe import QDataFrameView


class QHeaderViewBase(QtW.QHeaderView):
    """The header view for the QTableBase."""

    _Orientation: Qt.Orientation

    def __init__(self, parent: QTableBase | None = None) -> None:
        super().__init__(self._Orientation, parent)
        self.setSelectionMode(QtW.QHeaderView.SelectionMode.SingleSelection)
        self.setSectionsClickable(True)
        self.sectionPressed.connect(self._on_section_pressed)  # pressed
        self.sectionClicked.connect(self._on_section_clicked)  # released
        self.sectionEntered.connect(self._on_section_entered)  # dragged

    # fmt: off
    if TYPE_CHECKING:
        def parentWidget(self) -> QTableBase: ...
    # fmt: on

    @property
    def selection_model(self):
        return self.parentWidget()._selection_model

    def _on_section_pressed(self, logicalIndex: int) -> None:
        self.selection_model.jump_to(*self._index_for_selection_model(logicalIndex))
        self.selection_model.set_shift(True)

    def _on_section_entered(self, logicalIndex: int) -> None:
        self.selection_model.move_to(*self._index_for_selection_model(logicalIndex))

    def _on_section_clicked(self, logicalIndex) -> None:
        self.selection_model.set_shift(False)

    def _iter_selections(self) -> Iterator[slice]:
        """Iterate selections"""
        raise NotImplementedError()

    def _index_for_selection_model(self, logicalIndex: int) -> tuple[int, int]:
        raise NotImplementedError()

    def visualRectAtIndex(self, index: int) -> QtCore.QRect:
        """Return the visual rect of the given index."""
        raise NotImplementedError()

    @staticmethod
    def drawBorder(painter: QtGui.QPainter, rect: QtCore.QRect):
        """Draw the opened border of a section."""
        raise NotImplementedError()

    def drawCurrent(self, painter: QtGui.QPainter):
        """Draw the current index if exists."""
        raise NotImplementedError()

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        super().paintEvent(event)
        painter = QtGui.QPainter(self.viewport())
        color = self.parentWidget()._selection_color

        pen = QtGui.QPen(color, 3)
        painter.setPen(pen)
        # paint selections
        try:
            for _slice in self._iter_selections():
                rect_start = self.visualRectAtIndex(_slice.start)
                rect_stop = self.visualRectAtIndex(_slice.stop - 1)
                rect = rect_start | rect_stop
                self.drawBorder(painter, rect)

            # paint current
            self.drawCurrent(painter)
        except Exception as e:
            warnings.warn(f"QHeaderViewBase.paintEvent failed {e}", RuntimeWarning)

    def mouseReleaseEvent(self, e: QtGui.QMouseEvent) -> None:
        self.selection_model.set_shift(False)
        if e.button() == Qt.MouseButton.RightButton:
            # show context menu on header.
            index = self.logicalIndexAt(e.pos())
            r0, c0 = self._index_for_selection_model(index)
            if not self.selection_model.contains((max(r0, 0), max(c0, 0))):
                self._on_section_pressed(index)
            if menu := self.parentWidget()._make_context_menu():
                menu.exec(e.globalPos())
        return super().mouseReleaseEvent(e)

    def keyPressEvent(self, e):
        self._update_press_release(e.modifiers())
        return super().keyPressEvent(e)

    def keyReleaseEvent(self, a0):
        self._update_press_release(a0.modifiers())
        return super().keyReleaseEvent(a0)

    def _update_press_release(self, mod: Qt.KeyboardModifier):
        has_ctrl = mod & Qt.KeyboardModifier.ControlModifier
        has_shift = mod & Qt.KeyboardModifier.ShiftModifier
        self.selection_model.set_shift(has_shift)
        self.selection_model.set_ctrl(has_ctrl)


class QHorizontalHeaderView(QHeaderViewBase):
    _Orientation = Qt.Orientation.Horizontal

    def visualRectAtIndex(self, index: int) -> QtCore.QRect:
        x = self.sectionViewportPosition(index)
        y = self.rect().top()
        height = self.height()
        width = self.sectionSize(index)
        return QtCore.QRect(x, y, width, height)

    @staticmethod
    def drawBorder(painter: QtGui.QPainter, rect: QtCore.QRect):
        return painter.drawPolyline(
            rect.bottomLeft(),
            rect.topLeft(),
            rect.topRight(),
            rect.bottomRight(),
        )

    def drawCurrent(self, painter: QtGui.QPainter):
        row, col = self.selection_model.current_index
        if row < 0 and col >= 0:
            rect_current = self.visualRectAtIndex(col)
            rect_current.adjust(1, 1, -1, -1)
            color = self.parentWidget()._current_color
            pen = QtGui.QPen(color, 3)
            painter.setPen(pen)
            painter.drawRect(rect_current)

    def paintSection(self, painter, rect, logicalIndex):
        painter.save()
        super().paintSection(painter, rect, logicalIndex)
        painter.restore()
        # paint sort indicator
        if (
            isinstance(_proxy := self.parentWidget()._table_proxy(), proxy.SortProxy)
            and logicalIndex == _proxy.index
        ):
            # Draw sort indicator arrow
            size = 4
            try:
                arrow_x = rect.right() - size * 2 - 2
                center_y = rect.center().y() + 2
                _a = 1 if _proxy.ascending else -1
                # Draw up or down arrow
                arrow = QtGui.QPolygon(
                    [
                        QtCore.QPoint(arrow_x, center_y + _a * size),
                        QtCore.QPoint(arrow_x - size, center_y - _a * size),
                        QtCore.QPoint(arrow_x + size, center_y - _a * size),
                    ]
                )
                color = self.palette().color(QtGui.QPalette.ColorRole.WindowText)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QtGui.QBrush(color))
                painter.drawPolygon(arrow)
            except Exception as e:
                warnings.warn(
                    f"QHorizontalHeaderView.paintSection failed: {e}", RuntimeWarning
                )

    def _iter_selections(self):
        yield from self.selection_model.iter_col_selections()

    def _index_for_selection_model(self, logicalIndex):
        return -1, logicalIndex


class QVerticalHeaderView(QHeaderViewBase):
    _Orientation = Qt.Orientation.Vertical

    def visualRectAtIndex(self, index: int) -> QtCore.QRect:
        x = self.rect().left()
        y = self.sectionViewportPosition(index)
        height = self.sectionSize(index)
        width = self.width()
        return QtCore.QRect(x, y, width, height)

    @staticmethod
    def drawBorder(painter: QtGui.QPainter, rect: QtCore.QRect):
        return painter.drawPolyline(
            rect.topRight(),
            rect.topLeft(),
            rect.bottomLeft(),
            rect.bottomRight(),
        )

    def drawCurrent(self, painter: QtGui.QPainter):
        row, col = self.selection_model.current_index
        if col < 0 and row >= 0:
            rect_current = self.visualRectAtIndex(row)
            rect_current.adjust(1, 1, -1, -1)
            color = self.parentWidget()._current_color
            pen = QtGui.QPen(color, 4)
            painter.setPen(pen)
            painter.drawRect(rect_current)
        return None

    def _iter_selections(self):
        yield from self.selection_model.iter_row_selections()

    def _index_for_selection_model(self, logicalIndex):
        return logicalIndex, -1


class QDraggableHorizontalHeader(QHorizontalHeaderView):
    """Header view for DataFrameView that supports drag and drop."""

    def __init__(self, parent: QDataFrameView):
        super().__init__(parent)
        self._table_view_ref = weakref.ref(parent)
        self.setMouseTracking(True)
        self._hover_drag_indicator = QDraggableArea(self)
        self._hover_drag_indicator.setWindowFlags(
            QtCore.Qt.WindowType.FramelessWindowHint
        )
        self._hover_drag_indicator.setFixedSize(14, 14)
        self._hover_drag_indicator.hide()
        self._hover_drag_indicator.dragged.connect(self._drag_event)
        self._drag_enabled = True

    def mouseMoveEvent(self, e: QtGui.QMouseEvent):
        view = self._table_view_ref()
        if view is None or not self._drag_enabled:
            return super().mouseMoveEvent(e)
        if e.button() == QtCore.Qt.MouseButton.NoButton:
            # hover
            index = self.logicalIndexAt(e.pos())
            self._process_move_event(index)
        return super().mouseMoveEvent(e)

    def _process_move_event(self, index: int):
        view = self._table_view_ref()
        hovered_column_selected = False
        for sel in view.selection_model.iter_col_selections():
            if sel.start <= index < sel.stop:
                hovered_column_selected = True
                break
        if hovered_column_selected and index >= 0:
            index_rect = self.visualRectAtIndex(index)
            top_right = index_rect.topRight()
            top_right.setX(top_right.x() - 14)
            dy = (index_rect.height() - self._hover_drag_indicator.height()) / 2
            top_right.setY(top_right.y() + int(dy))
            self._hover_drag_indicator.move(top_right)
            self._hover_drag_indicator.show()
        else:
            self._hover_drag_indicator.hide()

    def leaveEvent(self, a0):
        self._hover_drag_indicator.hide()
        return super().leaveEvent(a0)

    def _data_model_for_drag(self) -> QtGui.QDrag | None:
        view = self._table_view_ref()
        if view is None or not self._drag_enabled:
            return
        cols = [sel.start for sel in view.selection_model.iter_col_selections()]
        model = view.to_model()
        df = wrap_dataframe(model.value)
        s = "" if len(cols) == 1 else "s"
        return drag_command(
            view,
            "builtins:QDataFrameView:select-columns",
            StandardType.DATAFRAME,
            with_params={"columns": cols},
            desc=f"{df.num_columns()} column{s}",
            text_data=lambda: df.to_csv_string("\t"),
            exec=False,
        )

    def _drag_event(self):
        if drag := self._data_model_for_drag():
            drag.exec()
