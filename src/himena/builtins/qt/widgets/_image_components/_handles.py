from __future__ import annotations
from typing import TYPE_CHECKING
from psygnal import Signal
from qtpy import QtWidgets as QtW, QtCore, QtGui
from qtpy.QtCore import Qt

from ._roi_items import (
    QLineRoi,
    QPointRoi,
    QPointsRoi,
    QPolygonRoi,
    QRectangleRoi,
    QEllipseRoi,
    QSegmentedLineRoi,
)

if TYPE_CHECKING:
    from ._graphics_view import QImageGraphicsView, QBaseGraphicsScene


class QHandleRect(QtW.QGraphicsRectItem):
    """The rect item for the ROI handles"""

    # NOTE: QGraphicsItem is not a QObject, so we can't use QtCore.Signal here
    moved_by_mouse = Signal(QtW.QGraphicsSceneMouseEvent)

    def __init__(self, x: int, y: int, width: int, height: int, parent=None):
        super().__init__(x, y, width, height, parent)
        self.setAcceptedMouseButtons(Qt.MouseButton.LeftButton)
        # this flag is needed to trigger mouseMoveEvent
        self.setFlag(QtW.QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self._pos_drag_start: QtCore.QPointF | None = None
        self._pos_drag_prev: QtCore.QPointF | None = None
        self._cursor_shape = Qt.CursorShape.PointingHandCursor
        self.setCursor(self._cursor_shape)
        self.setZValue(100000)

    def setColor(self, color: QtGui.QColor):
        self.setBrush(QtGui.QBrush(color))

    def center(self) -> QtCore.QPointF:
        """Return the center of the rect."""
        return self.rect().center()

    def setCenter(self, point: QtCore.QPointF):
        """Set the center of the rect."""
        x, y = point.x(), point.y()
        w, h = self.rect().width(), self.rect().height()
        self.setRect(x - w / 2, y - h / 2, w, h)

    def setSize(self, size: float):
        """Set the size of the rect."""
        x, y = self.center().x(), self.center().y()
        self.setRect(x - size / 2, y - size / 2, size, size)

    def translate(self, dx: float, dy: float):
        self.setRect(self.rect().translated(dx, dy))

    def mousePressEvent(self, event: QtW.QGraphicsSceneMouseEvent):
        grab = self.scene().grabSource()
        if grab is not None and grab is not self:
            return super().mousePressEvent(event)
        if event.button() == Qt.MouseButton.LeftButton:
            view = self.view()
            view.set_mode(self.view().Mode.SELECT)
            self.scene().setGrabSource(self)
        return super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QtW.QGraphicsSceneMouseEvent | None) -> None:
        if self.scene().grabSource() is not self:
            return super().mouseMoveEvent(event)
        self.moved_by_mouse.emit(event)
        return super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QtW.QGraphicsSceneMouseEvent | None) -> None:
        self.view().set_mode(self.view()._last_mode_before_key_hold)
        self.scene().setGrabSource(None)
        return super().mouseReleaseEvent(event)

    def view(self) -> QImageGraphicsView:
        return self.scene().views()[0]

    def scene(self) -> QBaseGraphicsScene:
        return super().scene()


class RoiSelectionHandles:
    draw_finished = Signal()

    def __init__(self, view: QImageGraphicsView):
        self._view = view
        self._handle_size = 2
        self._pen = QtGui.QPen(Qt.GlobalColor.black, 2)
        self._pen.setCosmetic(True)
        self._brush = QtGui.QBrush(Qt.GlobalColor.white)
        self._edge_color = QtGui.QColor(Qt.GlobalColor.red)
        self._handles: list[QHandleRect] = []
        # This attribute is needed for drawing polygons and segmented lines.
        # When the mouse is hovering, the last vertice should not be considered as a
        # point yet, until the mouse is clicked.
        self._is_drawing_polygon = False
        self._is_last_vertex_added = False

    def make_handle_at(
        self,
        pos: QtCore.QPointF,
        color: QtGui.QColor | None = None,
    ) -> QHandleRect:
        """Construct a handle at the given position and add to the view."""
        s = self._handle_size
        handle = QHandleRect(pos.x() - s / 2, pos.y() - s / 2, s, s)
        handle.setPen(self._pen)
        handle.setBrush(self._brush)
        self._handles.append(handle)
        self.view().scene().addItem(handle)
        if color:
            handle.setColor(color)
        return handle

    def update_handle_size(self, scale: float):
        self._handle_size = 4 / scale
        for handle in self._handles:
            handle.setSize(self._handle_size)

    def translate(self, dx: float, dy: float):
        for handle in self._handles:
            handle.setCenter(handle.rect().center() + QtCore.QPointF(dx, dy))

    def moveBy(self, dx: float, dy: float):
        for handle in self._handles:
            handle.moveBy(dx, dy)

    def clear_handles(self):
        """Remove all handles from the view."""
        view = self.view()
        for handle in self._handles:
            view.scene().removeItem(handle)
            handle.moved_by_mouse.disconnect()
        self._handles.clear()
        self.draw_finished.disconnect()

    def connect_line(self, line: QLineRoi):
        self.clear_handles()
        _line = line.line()
        h1 = self.make_handle_at(_line.p1())
        h2 = self.make_handle_at(_line.p2())
        hc = self.make_handle_at(_line.center(), self._edge_color)
        self._handles = [h1, h2, hc]

        @h1.moved_by_mouse.connect
        def _1_moved(ev: QtW.QGraphicsSceneMouseEvent):
            qline = line.line()
            qline.setP1(ev.pos())
            line.setLine(qline)

        @h2.moved_by_mouse.connect
        def _2_moved(ev: QtW.QGraphicsSceneMouseEvent):
            qline = line.line()
            qline.setP2(ev.pos())
            line.setLine(qline)

        @hc.moved_by_mouse.connect
        def _c_moved(ev: QtW.QGraphicsSceneMouseEvent):
            delta = ev.pos() - ev.lastPos()
            qline = line.line()
            qline.translate(delta.x(), delta.y())
            line.setLine(qline)

        @line.changed.connect
        def _line_changed(qline: QtCore.QLineF):
            h1.setCenter(qline.p1())
            h2.setCenter(qline.p2())
            hc.setCenter(qline.center())

    def connect_rect(self, rect: QRectangleRoi | QEllipseRoi):
        self.clear_handles()
        _rect = rect.rect()
        h_tl = self.make_handle_at(_rect.topLeft())
        h_br = self.make_handle_at(_rect.bottomRight())
        h_tr = self.make_handle_at(_rect.topRight())
        h_bl = self.make_handle_at(_rect.bottomLeft())
        h_t = self.make_handle_at(
            (_rect.topLeft() + _rect.topRight()) / 2, self._edge_color
        )
        h_b = self.make_handle_at(
            (_rect.bottomLeft() + _rect.bottomRight()) / 2, self._edge_color
        )
        h_l = self.make_handle_at(
            (_rect.topLeft() + _rect.bottomLeft()) / 2, self._edge_color
        )
        h_r = self.make_handle_at(
            (_rect.topRight() + _rect.bottomRight()) / 2, self._edge_color
        )
        self._handles = [h_tl, h_br, h_tr, h_bl, h_t, h_b, h_l, h_r]

        @h_tl.moved_by_mouse.connect
        def _tl_moved(ev: QtW.QGraphicsSceneMouseEvent):
            other = rect.rect().bottomRight()
            x0, x1 = sorted([other.x(), ev.pos().x()])
            y0, y1 = sorted([other.y(), ev.pos().y()])
            rect.setRect(x0, y0, x1 - x0, y1 - y0)

        @h_br.moved_by_mouse.connect
        def _br_moved(ev: QtW.QGraphicsSceneMouseEvent):
            other = rect.rect().topLeft()
            x0, x1 = sorted([other.x(), ev.pos().x()])
            y0, y1 = sorted([other.y(), ev.pos().y()])
            rect.setRect(x0, y0, x1 - x0, y1 - y0)

        @h_tr.moved_by_mouse.connect
        def _tr_moved(ev: QtW.QGraphicsSceneMouseEvent):
            other = rect.rect().bottomLeft()
            x0, x1 = sorted([other.x(), ev.pos().x()])
            y0, y1 = sorted([other.y(), ev.pos().y()])
            rect.setRect(x0, y0, x1 - x0, y1 - y0)

        @h_bl.moved_by_mouse.connect
        def _bl_moved(ev: QtW.QGraphicsSceneMouseEvent):
            other = rect.rect().topRight()
            x0, x1 = sorted([other.x(), ev.pos().x()])
            y0, y1 = sorted([other.y(), ev.pos().y()])
            rect.setRect(x0, y0, x1 - x0, y1 - y0)

        @h_t.moved_by_mouse.connect
        def _t_moved(ev: QtW.QGraphicsSceneMouseEvent):
            r0 = rect.rect()
            y0, y1 = sorted([r0.bottom(), ev.pos().y()])
            rect.setRect(r0.x(), y0, r0.width(), y1 - y0)

        @h_b.moved_by_mouse.connect
        def _b_moved(ev: QtW.QGraphicsSceneMouseEvent):
            r0 = rect.rect()
            y0, y1 = sorted([r0.top(), ev.pos().y()])
            rect.setRect(r0.x(), y0, r0.width(), y1 - y0)

        @h_l.moved_by_mouse.connect
        def _l_moved(ev: QtW.QGraphicsSceneMouseEvent):
            r0 = rect.rect()
            x0, x1 = sorted([r0.right(), ev.pos().x()])
            rect.setRect(x0, r0.y(), x1 - x0, r0.height())

        @h_r.moved_by_mouse.connect
        def _r_moved(ev: QtW.QGraphicsSceneMouseEvent):
            r0 = rect.rect()
            x0, x1 = sorted([r0.left(), ev.pos().x()])
            rect.setRect(x0, r0.y(), x1 - x0, r0.height())

        @rect.changed.connect
        def _rect_changed(r: QtCore.QRectF):
            tl = r.topLeft()
            br = r.bottomRight()
            tr = r.topRight()
            bl = r.bottomLeft()
            h_tl.setCenter(tl)
            h_br.setCenter(br)
            h_tr.setCenter(tr)
            h_bl.setCenter(bl)
            h_t.setCenter((tl + tr) / 2)
            h_b.setCenter((bl + br) / 2)
            h_l.setCenter((tl + bl) / 2)
            h_r.setCenter((tr + br) / 2)

    def connect_path(self, path: QPolygonRoi | QSegmentedLineRoi):
        self.clear_handles()
        _path = path.path()
        for i in range(_path.elementCount()):
            element = _path.elementAt(i)
            h = self.make_handle_at(QtCore.QPointF(element.x, element.y))
            h.moved_by_mouse.connect(lambda ev, i=i: path.update_point(i, ev.pos()))

        @path.changed.connect
        def _path_changed(p: QtGui.QPainterPath):
            offset = 0 if self._is_last_vertex_added else 1
            for i in range(p.elementCount() - offset, len(self._handles)):
                self.view().scene().removeItem(self._handles[i])
            del self._handles[p.elementCount() - offset :]
            for i in range(len(self._handles), p.elementCount() - offset):
                element = p.elementAt(i)
                h = self.make_handle_at(QtCore.QPointF(element.x, element.y))
                h.moved_by_mouse.connect(lambda ev, i=i: path.update_point(i, ev.pos()))
            for i, h in enumerate(self._handles):
                element = p.elementAt(i)
                h.setCenter(QtCore.QPointF(element.x, element.y))

        if isinstance(path, QPolygonRoi):
            self.draw_finished.connect(lambda: self._finish_drawing_path(path))
        else:
            self.draw_finished.connect(lambda: self._finish_drawing_path(path))

    def connect_point(self, point: QPointRoi):
        self.clear_handles()
        h = self.make_handle_at(point.point())
        h.moved_by_mouse.connect(lambda ev: point.setPoint(ev.pos()))

        @point.changed.connect
        def _point_changed(ps: QtCore.QPointF):
            h.setCenter(ps)

    def connect_points(self, points: QPointsRoi):
        self.clear_handles()
        for i in range(points.count()):
            h = self.make_handle_at(points.pointAt(i))
            h.moved_by_mouse.connect(lambda ev, i=i: points.update_point(i, ev.pos()))

        @points.changed.connect
        def _points_changed(ps: list[QtCore.QPointF]):
            for i in range(len(ps), len(self._handles)):
                self.view().scene().removeItem(self._handles[i])
            del self._handles[len(ps) :]
            for i in range(len(self._handles), len(ps)):
                h = self.make_handle_at(ps[i])
                h.moved_by_mouse.connect(
                    lambda ev, i=i: points.update_point(i, ev.pos())
                )
            for i, h in enumerate(self._handles):
                h.setCenter(ps[i])

    def _finish_drawing_path(self, path: QPolygonRoi | QSegmentedLineRoi):
        painter_path = path.path()
        if isinstance(path, QPolygonRoi):
            painter_path.closeSubpath()
        path.setPath(painter_path)

    def view(self) -> QImageGraphicsView:
        return self._view

    def start_drawing_polygon(self):
        self._is_drawing_polygon = True
        self._is_last_vertex_added = False

    def is_drawing_polygon(self) -> bool:
        return self._is_drawing_polygon

    def finish_drawing_polygon(self):
        self._is_drawing_polygon = False
        self.draw_finished.emit()
