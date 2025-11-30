from __future__ import annotations

import math
import logging
from typing import TYPE_CHECKING, Generic, TypeVar
from qtpy import QtGui, QtCore
from qtpy.QtCore import Qt
from himena_builtins.qt.widgets._image_components._roi_items import (
    QPointRoi,
    QPointsRoi,
    QPolygonRoi,
    QRoi,
    QLineRoi,
    QCircleRoi,
    QRectangleRoi,
    QEllipseRoi,
    QRotatedRectangleRoi,
    QRotatedEllipseRoi,
    QSegmentedLineRoi,
)
from himena_builtins.qt.widgets._image_components._handles import RoiSelectionHandles
from himena.standards.mouse import MouseEventHandler
from himena.widgets import show_tooltip

if TYPE_CHECKING:
    from ._graphics_view import QImageGraphicsView

_LOGGER = logging.getLogger(__name__)
_R = TypeVar("_R", bound=QRoi)
_R1 = TypeVar("_R1", bound=QSegmentedLineRoi)


class QtMouseEvent(MouseEventHandler[QtGui.QMouseEvent]):
    def __init__(self, view: QImageGraphicsView):
        self._view = view
        self._pos_drag_start: QtCore.QPoint | None = None
        self._pos_drag_prev: QtCore.QPoint | None = None

    @property
    def selection_handles(self) -> RoiSelectionHandles:
        return self._view._selection_handles

    def _mouse_move_pan_zoom(self, pos: QtCore.QPointF):
        delta = pos - self._pos_drag_prev
        self._view.move_items_by(delta.x(), delta.y())

    def pressed(self, event):
        self._pos_drag_start = event.pos()
        self._pos_drag_prev = event.pos()

    def released(self, event):
        self._pos_drag_prev = None
        self._pos_drag_start = None

    def is_click(self, event: QtGui.QMouseEvent) -> bool:
        """Check if the event is a click."""
        return (
            self._pos_drag_start is not None
            and (self._pos_drag_start - event.pos()).manhattanLength() < 2
        )


class PanZoomMouseEvents(QtMouseEvent):
    def pressed(self, event):
        super().pressed(event)
        self._view.viewport().setCursor(Qt.CursorShape.ClosedHandCursor)
        self._view.scene().setGrabSource(self)

    def moved(self, event):
        if self._pos_drag_start is None or self._pos_drag_prev is None:
            return
        self._mouse_move_pan_zoom(event.pos())
        self._pos_drag_prev = event.pos()

    def released(self, event):
        self._view.viewport().setCursor(Qt.CursorShape.ArrowCursor)
        return super().released(event)

    def double_clicked(self, event):
        self._view.fitInView(self._view.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)


class SelectMouseEvents(QtMouseEvent):
    def pressed(self, event):
        super().pressed(event)
        self._view.select_item_at(self._view.mapToScene(event.pos()))
        self._view.scene().setGrabSource(self)

    def moved(self, event):
        if self._pos_drag_prev is None:
            return
        pos = self._view.mapToScene(event.pos())
        if item := self._view._current_roi_item:
            if self._pos_drag_prev is None:
                return
            x0, y0 = self._view._pos_to_tuple(
                self._view.mapToScene(self._pos_drag_prev)
            )
            x1, y1 = self._view._pos_to_tuple(pos)
            delta = QtCore.QPointF(x1 - x0, y1 - y0)
            item.translate(delta.x(), delta.y())
            self._view.current_roi_updated.emit()
        else:
            # just forward to the pan-zoom mode
            self._mouse_move_pan_zoom(event.pos())
        self._pos_drag_prev = event.pos()


class RoiMouseEvents(QtMouseEvent, Generic[_R]):
    def roi(self) -> _R:
        out = self._view._current_roi_item
        assert isinstance(out, self.roi_type())
        return out

    def roi_type(self) -> type[_R]:
        raise NotImplementedError

    def make_roi(self, x: float, y: float, pen: QtGui.QPen) -> _R:
        raise NotImplementedError


class _SingleDragRoiMouseEvents(RoiMouseEvents[_R]):
    def _update_roi(self, start: QtCore.QPointF, current: QtCore.QPointF):
        raise NotImplementedError

    def _coerce_pos(
        self,
        pos: QtCore.QPointF,
        pos0: QtCore.QPointF,
    ) -> tuple[QtCore.QPointF, QtCore.QPointF]:
        return pos, pos0

    def pressed(self, event: QtGui.QMouseEvent):
        super().pressed(event)
        self._view.remove_current_item(reason="start drawing new ROI")
        p = self._view.mapToScene(self._pos_drag_start)
        self.make_roi(p.x(), p.y(), self._view._roi_pen)
        self.selection_handles.update_handle_size(self._view.transform().m11())

    def moved(self, event: QtGui.QMouseEvent):
        if self._pos_drag_start is None or self._pos_drag_prev is None:
            return
        pos = self._view.mapToScene(event.pos())
        if isinstance(cur_item := self._view._current_roi_item, self.roi_type()):
            pos0 = self._view.mapToScene(self._pos_drag_start)
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                pos, pos0 = self._coerce_pos(pos, pos0)
            self._update_roi(pos0, pos)
            self._view.current_roi_updated.emit()
            xscale = yscale = self._view._scale_bar_widget._scale
            unit = self._view._scale_bar_widget._unit
            show_tooltip(cur_item.short_description(xscale, yscale, unit))

    def released(self, event: QtGui.QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            if self.is_click(event):
                self._view.remove_current_item(
                    reason=f"stop drawing {self._view.mode()}"
                )
        show_tooltip("")
        return super().released(event)

    def double_clicked(self, event):
        self._view.remove_current_item(reason="double-click")


class _LineTypeRoiMouseEvents(_SingleDragRoiMouseEvents[_R1]):
    def _coerce_pos(
        self,
        pos: QtCore.QPointF,
        pos0: QtCore.QPointF,
    ) -> tuple[QtCore.QPointF, QtCore.QPointF]:
        return _find_nice_position(pos, pos0), pos0


class _RectangleTypeRoiMouseEvents(_SingleDragRoiMouseEvents[_R]):
    def _coerce_pos(
        self,
        pos: QtCore.QPointF,
        pos0: QtCore.QPointF,
    ) -> tuple[QtCore.QPointF, QtCore.QPointF]:
        return _find_nice_rect_position(pos, pos0), pos0


class _MultiRoiMouseEvents(RoiMouseEvents[_R]):
    def pressed(self, event: QtGui.QMouseEvent):
        if (
            type(self._view._current_roi_item) is self.roi_type()
            and not self.selection_handles.is_drawing_polygon()
        ):
            # drawing the same ROI type, remove the previous one and end.
            self._view.remove_current_item(reason="start drawing new polygon")
            self._view.select_item(None)
        elif type(self._view._current_roi_item) is not self.roi_type():
            # just after switched from another ROI type, remove the previous one
            # and start drawing the current one.
            self._view.remove_current_item(reason="start drawing new ROI")
            self.selection_handles.start_drawing_polygon()
            self.selection_handles._is_last_vertex_added = True
        return super().pressed(event)

    def released(self, event: QtGui.QMouseEvent):
        if self._pos_drag_start is None:
            return
        if not self.is_click(event):
            return
        if self.selection_handles.is_drawing_polygon():
            p0 = self._view.mapToScene(self._pos_drag_start)
            item = self._view._current_roi_item
            if not isinstance(item, self.roi_type()):
                x1, y1 = p0.x(), p0.y()
                self.make_roi(x1, y1, self._view._roi_pen)
                self.selection_handles.update_handle_size(self._view.transform().m11())
            else:
                _LOGGER.info(
                    f"Added point {self._pos_drag_start} to {self._view.mode()}"
                )
                item.add_point(p0)
            self.selection_handles._is_last_vertex_added = True
            self._view.current_roi_updated.emit()
        return super().released(event)

    def double_clicked(self, event):
        self.selection_handles.finish_drawing_polygon()
        self._pos_drag_start = self._pos_drag_prev = None


class _SegmentedTypeRoiMouseEvents(_MultiRoiMouseEvents[_R1]):
    def moved(self, event: QtGui.QMouseEvent):
        pos = self._view.mapToScene(event.pos())
        if event.button() == Qt.MouseButton.NoButton:
            if self.selection_handles.is_drawing_polygon() and isinstance(
                item := self._view._current_roi_item, self.roi_type()
            ):
                # update the last point of the polygon
                if self.selection_handles._is_last_vertex_added:
                    self.selection_handles._is_last_vertex_added = False
                    item.add_point(pos)
                    self._view.current_roi_updated.emit()
                else:
                    num = item.count()
                    if num > 1:
                        item.update_point(num - 1, pos, self._view)
                        self._view.current_roi_updated.emit()


class PointsRoiMouseEvents(_MultiRoiMouseEvents[QPointsRoi]):
    def roi_type(self) -> type[QPointsRoi]:
        return QPointsRoi

    def make_roi(self, x: float, y: float, pen: QtGui.QPen) -> QPointsRoi:
        roi = QPointsRoi([x], [y]).withPen(pen)
        self._view.set_current_roi(roi)
        self.selection_handles.connect_points(roi)
        return roi

    def moved(self, event: QtGui.QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._mouse_move_pan_zoom(event.pos())
            self._pos_drag_prev = event.pos()
            return
        return super().moved(event)


class SegmentedLineRoiMouseEvents(_SegmentedTypeRoiMouseEvents[QSegmentedLineRoi]):
    def roi_type(self) -> type[QSegmentedLineRoi]:
        return QSegmentedLineRoi

    def make_roi(self, x: float, y: float, pen: QtGui.QPen) -> QSegmentedLineRoi:
        roi = QSegmentedLineRoi([x], [y]).withPen(pen)
        self._view.set_current_roi(roi)
        self.selection_handles.connect_path(roi)
        return roi


class PolygonRoiMouseEvents(_SegmentedTypeRoiMouseEvents[QPolygonRoi]):
    def roi_type(self) -> type[QPolygonRoi]:
        return QPolygonRoi

    def make_roi(self, x: float, y: float, pen: QtGui.QPen) -> QPolygonRoi:
        roi = QPolygonRoi([x], [y]).withPen(pen)
        self._view.set_current_roi(roi)
        self.selection_handles.connect_path(roi)
        return roi


class LineRoiMouseEvents(_LineTypeRoiMouseEvents[QLineRoi]):
    def roi_type(self) -> type[QLineRoi]:
        return QLineRoi

    def make_roi(self, x: float, y: float, pen: QtGui.QPen) -> QLineRoi:
        roi = QLineRoi(x, y, x, y).withPen(pen)
        self._view.set_current_roi(roi)
        self.selection_handles.connect_line(roi)
        return roi

    def _update_roi(self, start, current):
        if isinstance(item := self._view._current_roi_item, QLineRoi):
            item.setLine(start.x(), start.y(), current.x(), current.y())


class RotatedRectangleRoiMouseEvents(_LineTypeRoiMouseEvents[QRotatedRectangleRoi]):
    def roi_type(self) -> type[QRotatedRectangleRoi]:
        return QRotatedRectangleRoi

    def make_roi(self, x: float, y: float, pen: QtGui.QPen) -> QRotatedRectangleRoi:
        p0 = QtCore.QPointF(x, y)
        roi = QRotatedRectangleRoi(p0, p0).withPen(pen)
        self._view.set_current_roi(roi)
        self.selection_handles.connect_rotated_rect(roi)
        return roi

    def _update_roi(self, start, current):
        if isinstance(item := self._view._current_roi_item, QRotatedRectangleRoi):
            item.set_end(current)


class RotatedEllipseRoiMouseEvents(_LineTypeRoiMouseEvents[QRotatedEllipseRoi]):
    def roi_type(self) -> type[QRotatedEllipseRoi]:
        return QRotatedEllipseRoi

    def make_roi(self, x: float, y: float, pen: QtGui.QPen) -> QRotatedEllipseRoi:
        p0 = QtCore.QPointF(x, y)
        roi = QRotatedEllipseRoi(p0, p0).withPen(pen)
        self._view.set_current_roi(roi)
        self.selection_handles.connect_rotated_rect(roi)
        return roi

    def _update_roi(self, start, current):
        if isinstance(item := self._view._current_roi_item, QRotatedEllipseRoi):
            item.set_end(current)


class RectangleRoiMouseEvents(_RectangleTypeRoiMouseEvents[QRectangleRoi]):
    def roi_type(self) -> type[QRectangleRoi]:
        return QRectangleRoi

    def make_roi(self, x: float, y: float, pen: QtGui.QPen) -> QRectangleRoi:
        roi = QRectangleRoi(x, y, 0, 0).withPen(pen)
        self._view.set_current_roi(roi)
        self.selection_handles.connect_rect(roi)
        return roi

    def _update_roi(self, start, current):
        if isinstance(item := self._view._current_roi_item, QRectangleRoi):
            x0, y0 = self._view._pos_to_tuple(current)
            x1, y1 = self._view._pos_to_tuple(start)
            width = abs(x1 - x0)
            height = abs(y1 - y0)
            item.setRect(min(x0, x1), min(y0, y1), width, height)


class CircleRoiMouseEvents(_SingleDragRoiMouseEvents[QCircleRoi]):
    def roi_type(self) -> type[QCircleRoi]:
        return QCircleRoi

    def make_roi(self, x: float, y: float, pen: QtGui.QPen) -> QCircleRoi:
        roi = QCircleRoi(x, y, 0).withPen(pen)
        self._view.set_current_roi(roi)
        self.selection_handles.connect_circle(roi)
        return roi

    def _update_roi(self, start: QtCore.QPointF, current: QtCore.QPointF):
        if isinstance(item := self._view._current_roi_item, QCircleRoi):
            x0, y0 = self._view._pos_to_tuple(start)
            x1, y1 = self._view._pos_to_tuple(current)
            radius = min(abs(x1 - x0), abs(y1 - y0))
            item.setCenterAndRadius((x0, y0), radius)


class EllipseRoiMouseEvents(_RectangleTypeRoiMouseEvents[QEllipseRoi]):
    def roi_type(self) -> type[QEllipseRoi]:
        return QEllipseRoi

    def make_roi(self, x: float, y: float, pen: QtGui.QPen) -> QEllipseRoi:
        roi = QEllipseRoi(x, y, 0, 0).withPen(pen)
        self._view.set_current_roi(roi)
        self.selection_handles.connect_rect(roi)
        return roi

    def _update_roi(self, start, current):
        if isinstance(item := self._view._current_roi_item, QEllipseRoi):
            x0, y0 = self._view._pos_to_tuple(current)
            x1, y1 = self._view._pos_to_tuple(start)
            width = abs(x1 - x0)
            height = abs(y1 - y0)
            item.setRect(min(x0, x1), min(y0, y1), width, height)


class PointRoiMouseEvents(RoiMouseEvents[QPointRoi]):
    def roi_type(self) -> type[QPointRoi]:
        return QPointRoi

    def make_roi(self, x: float, y: float, pen: QtGui.QPen) -> QPointRoi:
        roi = QPointRoi(x, y).withPen(pen)
        self._view.set_current_roi(roi)
        self.selection_handles.connect_point(roi)
        return roi

    def moved(self, event: QtGui.QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._mouse_move_pan_zoom(event.pos())
            self._pos_drag_prev = event.pos()

    def released(self, event: QtGui.QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton and self.is_click(event):
            pos = self._view.mapToScene(event.pos())
            self._view.remove_current_item(reason=f"stop drawing {self._view.mode()}")
            self.make_roi(pos.x(), pos.y(), self._view._roi_pen)
            self.selection_handles.update_handle_size(self._view.transform().m11())
        return super().released(event)


def _find_nice_position(pos: QtCore.QPointF, pos0: QtCore.QPointF) -> QtCore.QPointF:
    """Find the "nice" position when Shift is pressed."""
    x0, y0 = pos0.x(), pos0.y()
    x1, y1 = pos.x(), pos.y()
    ang = math.atan2(y1 - y0, x1 - x0)
    pi = math.pi
    if -pi / 8 < ang <= pi / 8:  # right direction
        y1 = y0
    elif 3 * pi / 8 < ang <= 5 * pi / 8:  # down direction
        x1 = x0
    elif -5 * pi / 8 < ang <= -3 * pi / 8:  # up direction
        x1 = x0
    elif ang <= -7 * pi / 8 or 7 * pi / 8 < ang:  # left direction
        y1 = y0
    elif pi / 8 < ang <= 3 * pi / 8:  # down-right direction
        if abs(x1 - x0) > abs(y1 - y0):
            x1 = x0 + abs(y1 - y0)
        else:
            y1 = y0 + abs(x1 - x0)
    elif -3 * pi / 8 < ang <= -pi / 8:  # up-left direction
        if abs(x1 - x0) > abs(y1 - y0):
            x1 = x0 + abs(y1 - y0)
        else:
            y1 = y0 - abs(x1 - x0)
    elif 5 * pi / 8 < ang <= 7 * pi / 8:  # down-left direction
        if abs(x1 - x0) > abs(y1 - y0):
            x1 = x0 - abs(y1 - y0)
        else:
            y1 = y0 + abs(x1 - x0)
    elif -7 * pi / 8 < ang <= -5 * pi / 8:  # up-right direction
        if abs(x1 - x0) > abs(y1 - y0):
            x1 = x0 - abs(y1 - y0)
        else:
            y1 = y0 - abs(x1 - x0)
    return QtCore.QPointF(x1, y1)


def _find_nice_rect_position(
    pos: QtCore.QPointF, pos0: QtCore.QPointF
) -> QtCore.QPointF:
    x0, y0 = pos0.x(), pos0.y()
    x1, y1 = pos.x(), pos.y()
    dy, dx = y1 - y0, x1 - x0
    length = min(abs(dy), abs(dx))
    dy_sign = 1 if dy > 0 else -1
    dx_sign = 1 if dx > 0 else -1
    return QtCore.QPointF(x0 + dx_sign * length, y0 + dy_sign * length)
