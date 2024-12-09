from __future__ import annotations
from contextlib import contextmanager
import math

from qtpy import QtWidgets as QtW, QtCore, QtGui
from psygnal import Signal
import numpy as np
from typing import Iterable, Iterator

from himena.standards import roi
from himena.consts import MonospaceFontFamily


class QRoi(QtW.QGraphicsItem):
    """The base class for all ROI items."""

    def label(self) -> str:
        return getattr(self, "_roi_label", "")

    def setLabel(self, label: str):
        self._roi_label = label

    def toRoi(self, indices: Iterable[int | None]) -> roi.ImageRoi:
        raise NotImplementedError

    def translate(self, dx: float, dy: float):
        raise NotImplementedError

    def makeThumbnail(self, size: int) -> QtGui.QPixmap:
        raise NotImplementedError

    def withPen(self, pen: QtGui.QPen):
        self.setPen(pen)
        return self

    def withLabel(self, label: str | None):
        self.setLabel(label or "")
        return self

    def paint_label(self, painter: QtGui.QPainter, label: str, pos: QtCore.QPointF):
        _LABEL_TEXT_PEN = QtGui.QPen(QtGui.QColor(255, 255, 255), 1)
        _LABEL_TEXT_FONT = QtGui.QFont(MonospaceFontFamily, 10)
        _LABEL_FONT_METRICS = QtGui.QFontMetrics(_LABEL_TEXT_FONT)
        _LABEL_FONT_HEIGHT = _LABEL_FONT_METRICS.height()
        _LABEL_BG_BRUSH = QtGui.QBrush(QtGui.QColor(0, 0, 0, 200))
        painter.setBrush(_LABEL_BG_BRUSH)
        width = _LABEL_FONT_METRICS.width(label)
        off = 2
        painter.drawRect(
            pos.x() - off,
            pos.y() - off,
            width + 2 * off,
            _LABEL_FONT_HEIGHT + 2 * off,
        )
        painter.setPen(_LABEL_TEXT_PEN)
        painter.setFont(_LABEL_TEXT_FONT)
        painter.drawText(pos, label)

    def _thumbnail_transform(self, size: int) -> QtGui.QTransform:
        rect = self.boundingRect()
        transform = QtGui.QTransform()
        rect_size = max(rect.width(), rect.height())
        if rect_size == 0:
            rect_size = 1
        transform.translate(size / 2, size / 2)
        transform.scale((size - 2) / rect_size, (size - 2) / rect_size)
        transform.translate(-rect.center().x(), -rect.center().y())
        return transform

    def _pen_thumbnail(self) -> QtGui.QPen:
        pen = QtGui.QPen(self.pen())
        pen.setWidth(1)
        return pen

    def _roi_type(self) -> str:
        return self.__class__.__name__


class QLineRoi(QtW.QGraphicsLineItem, QRoi):
    changed = Signal(QtCore.QLineF)

    def toRoi(self, indices) -> roi.LineRoi:
        line = self.line()
        return roi.LineRoi(
            x1=line.x1(),
            y1=line.y1(),
            x2=line.x2(),
            y2=line.y2(),
            indices=indices,
            name=self.label(),
        )

    def translate(self, dx: float, dy: float):
        new_line = self.line()
        new_line.translate(dx, dy)
        self.setLine(new_line)

    def setLine(self, *args):
        super().setLine(*args)
        self.changed.emit(self.line())

    def makeThumbnail(self, size: int) -> QtGui.QPixmap:
        pixmap = QtGui.QPixmap(size, size)
        pixmap.fill(QtCore.Qt.GlobalColor.black)
        painter = QtGui.QPainter(pixmap)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        painter.setPen(self._pen_thumbnail())
        painter.setTransform(self._thumbnail_transform(size))
        painter.drawLine(self.line())
        painter.end()
        return pixmap

    def _roi_type(self) -> str:
        return "line"


class QRectRoiBase(QRoi):
    changed = Signal(QtCore.QRectF)


class QRectangleRoi(QtW.QGraphicsRectItem, QRectRoiBase):
    def toRoi(self, indices) -> roi.RectangleRoi:
        rect = self.rect()
        return roi.RectangleRoi(
            x=rect.x(),
            y=rect.y(),
            width=rect.width(),
            height=rect.height(),
            indices=indices,
            name=self.label(),
        )

    def setRect(self, *args):
        super().setRect(*args)
        self.changed.emit(self.rect())

    def translate(self, dx: float, dy: float):
        new_rect = self.rect()
        new_rect.translate(dx, dy)
        self.setRect(new_rect)

    def makeThumbnail(self, size: int) -> QtGui.QPixmap:
        pixmap = QtGui.QPixmap(size, size)
        pixmap.fill(QtCore.Qt.GlobalColor.black)
        painter = QtGui.QPainter(pixmap)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        painter.setPen(self._pen_thumbnail())
        painter.setTransform(self._thumbnail_transform(size))
        painter.drawRect(self.rect())
        painter.end()
        return pixmap

    def _roi_type(self) -> str:
        return "rectangle"


class QEllipseRoi(QtW.QGraphicsEllipseItem, QRectRoiBase):
    changed = Signal(QtCore.QRectF)

    def toRoi(self, indices) -> roi.EllipseRoi:
        rect = self.rect()
        return roi.EllipseRoi(
            x=rect.x(),
            y=rect.y(),
            width=rect.width(),
            height=rect.height(),
            indices=indices,
            name=self.label(),
        )

    def setRect(self, *args):
        super().setRect(*args)
        self.changed.emit(self.rect())

    def translate(self, dx: float, dy: float):
        new_rect = self.rect()
        new_rect.translate(dx, dy)
        self.setRect(new_rect)

    def makeThumbnail(self, size: int) -> QtGui.QPixmap:
        pixmap = QtGui.QPixmap(size, size)
        pixmap.fill(QtCore.Qt.GlobalColor.black)
        painter = QtGui.QPainter(pixmap)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        painter.setPen(self._pen_thumbnail())
        painter.setTransform(self._thumbnail_transform(size))
        painter.drawEllipse(self.rect())
        painter.end()
        return pixmap

    def _roi_type(self) -> str:
        return "ellipse"


class QRotatedRectangleRoi(QRoi):
    changed = Signal(object)

    def __init__(self, left: QtCore.QPointF, right: QtCore.QPointF, height: float = 50):
        super().__init__()
        dr = right - left
        width = math.sqrt(dr.x() ** 2 + dr.y() ** 2)
        center = (left + right) / 2
        rad = math.atan2(dr.y(), dr.x())
        self._center = center
        self._angle = math.degrees(rad)
        self._width = width
        self._height = height
        self._pen = QtGui.QPen()
        self.setLeft(left)
        self.setRight(right)

    def vector_x(self) -> QtCore.QPointF:
        rad = math.radians(self.angle())
        return QtCore.QPointF(math.cos(rad), math.sin(rad)) * self._width

    def vector_y(self) -> QtCore.QPointF:
        rad = math.radians(self.angle())
        return QtCore.QPointF(-math.sin(rad), math.cos(rad)) * self._height

    def angle(self) -> float:
        return self._angle

    def left(self) -> QtCore.QPointF:
        """Return the left anchor point."""
        return self._center - self.vector_x() / 2

    def right(self) -> QtCore.QPointF:
        """Return the right anchor point."""
        return self._center + self.vector_x() / 2

    def top(self) -> QtCore.QPointF:
        """Return the top anchor point."""
        return self._center - self.vector_y() / 2

    def bottom(self) -> QtCore.QPointF:
        """Return the bottom anchor point."""
        return self._center + self.vector_y() / 2

    def center(self) -> QtCore.QPointF:
        return self._center

    def setLeft(self, left: QtCore.QPointF):
        right = self.right()
        vecx = right - left
        with self._update_and_emit():
            self._angle = math.degrees(math.atan2(vecx.y(), vecx.x()))
            self._width = math.sqrt(vecx.x() ** 2 + vecx.y() ** 2)
            self._center = (left + right) / 2

    def setRight(self, right: QtCore.QPointF):
        left = self.left()
        vecx = right - left
        with self._update_and_emit():
            self._angle = math.degrees(math.atan2(vecx.y(), vecx.x()))
            self._width = math.sqrt(vecx.x() ** 2 + vecx.y() ** 2)
            self._center = (left + right) / 2

    def setHeight(self, height: float):
        with self._update_and_emit():
            self._height = height

    def toRoi(self, indices) -> roi.RotatedRectangleRoi:
        return roi.RotatedRectangleRoi(
            x=self._center.x(),
            y=self._center.y(),
            width=self._width,
            height=self._height,
            angle=self._angle,
            indices=indices,
            name=self.label(),
        )

    def pen(self) -> QtGui.QPen:
        return self._pen

    def setPen(self, pen: QtGui.QPen):
        self._pen = QtGui.QPen(pen)
        self.update()

    def translate(self, dx: float, dy: float):
        self._center += QtCore.QPointF(dx, dy)
        self._update_and_emit()

    def _update_and_emit(self):
        self.update()
        self.changed.emit(self)

    @contextmanager
    def _update_and_emit(self):
        old_bbox = self.boundingRect()
        yield
        new_bbox = self.boundingRect()
        self.changed.emit(self)
        self.update()
        if scene := self.scene():
            scene.update(self.mapRectToScene(old_bbox.united(new_bbox)))

    def _corner_points(self) -> list[QtCore.QPointF]:
        center = self.center()
        vx = self.vector_x()
        vy = self.vector_y()
        p00 = center - vx / 2 - vy / 2
        p01 = center - vx / 2 + vy / 2
        p10 = center + vx / 2 - vy / 2
        p11 = center + vx / 2 + vy / 2
        return p00, p01, p11, p10

    def paint(self, painter, option, widget):
        painter.setPen(self.pen())
        painter.drawPolygon(*self._corner_points())

    def boundingRect(self):
        points = self._corner_points()
        xmin = min(p.x() for p in points)
        xmax = max(p.x() for p in points)
        ymin = min(p.y() for p in points)
        ymax = max(p.y() for p in points)
        return QtCore.QRectF(xmin, ymin, xmax - xmin, ymax - ymin)

    def _roi_type(self) -> str:
        return "rotated rectangle"


class QSegmentedLineRoi(QtW.QGraphicsPathItem, QRoi):
    changed = Signal(QtGui.QPainterPath)

    def __init__(self, xs: Iterable[float], ys: Iterable[float], parent=None):
        super().__init__(parent)
        path = QtGui.QPainterPath()
        path.moveTo(xs[0], ys[0])
        for x, y in zip(xs[1:], ys[1:]):
            path.lineTo(x, y)
        self.setPath(path)

    def toRoi(self, indices) -> roi.SegmentedLineRoi:
        path = self.path()
        xs, ys = [], []
        for i in range(path.elementCount()):
            element = path.elementAt(i)
            xs.append(element.x)
            ys.append(element.y)
        return roi.SegmentedLineRoi(xs=xs, ys=ys, indices=indices, name=self.label())

    def setPath(self, *args):
        super().setPath(*args)
        self.changed.emit(self.path())

    def translate(self, dx: float, dy: float):
        new_path = self.path()
        new_path.translate(dx, dy)
        self.setPath(new_path)

    def add_point(self, pos: QtCore.QPointF):
        path = self.path()
        if path.elementCount() == 0:
            path.moveTo(pos)
        else:
            path.lineTo(pos)
        self.setPath(path)

    def count(self) -> int:
        """Number of points in the line."""
        return self.path().elementCount()

    def update_point(self, ith: int, pos: QtCore.QPointF):
        path = self.path()
        path.setElementPositionAt(ith, pos.x(), pos.y())
        self.setPath(path)

    def makeThumbnail(self, size: int) -> QtGui.QPixmap:
        pixmap = QtGui.QPixmap(size, size)
        pixmap.fill(QtCore.Qt.GlobalColor.black)
        painter = QtGui.QPainter(pixmap)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        painter.setPen(self._pen_thumbnail())
        painter.setTransform(self._thumbnail_transform(size))
        painter.drawPath(self.path())
        painter.end()
        return pixmap

    def _roi_type(self) -> str:
        return "segmented line"


class QPolygonRoi(QSegmentedLineRoi):
    def toRoi(self, indices) -> roi.PolygonRoi:
        path = self.path()
        xs, ys = [], []
        for i in range(path.elementCount()):
            element = path.elementAt(i)
            xs.append(element.x)
            ys.append(element.y)
        return roi.PolygonRoi(xs=xs, ys=ys, indices=indices, name=self.label())

    def _roi_type(self) -> str:
        return "polygon"


class QPointRoiBase(QRoi):
    def __init__(self, parent):
        super().__init__(parent)
        self._pen = QtGui.QPen(QtGui.QColor(0, 0, 0), 2)
        self._pen.setCosmetic(True)
        self._pen.setJoinStyle(QtCore.Qt.PenJoinStyle.MiterJoin)
        self._brush = QtGui.QBrush(QtGui.QColor(225, 225, 0))
        self._size = 8
        symbol_square = QtGui.QPainterPath()
        symbol_square.moveTo(-self._size, 0)
        symbol_square.lineTo(self._size, 0)
        symbol_square.moveTo(0, -self._size)
        symbol_square.lineTo(0, self._size)
        symbol_square.addRect(-self._size / 2, -self._size / 2, self._size, self._size)
        self._symbol = symbol_square
        self._bounding_rect_cache: QtCore.QRectF | None = None

    def pen(self) -> QtGui.QPen:
        return self._pen

    def setPen(self, pen: QtGui.QPen):
        self._pen = pen

    def brush(self) -> QtGui.QBrush:
        return self._brush

    def setBrush(self, brush: QtGui.QBrush):
        self._brush = brush

    def _iter_points(self) -> Iterator[QtCore.QPointF]:
        raise NotImplementedError

    def paint(
        self,
        painter: QtGui.QPainter,
        option: QtW.QStyleOptionGraphicsItem,
        widget: QtW.QWidget,
    ):
        painter.setPen(self.pen())
        painter.setBrush(self.brush())
        tr = painter.transform()

        for pt in self._iter_points():
            painter.resetTransform()
            xy_transformed = tr.map(pt)
            painter.translate(xy_transformed)
            painter.drawPath(self._symbol)
        self.scene().update()

    def makeThumbnail(self, size: int) -> QtGui.QPixmap:
        pixmap = QtGui.QPixmap(size, size)
        pixmap.fill(QtCore.Qt.GlobalColor.black)
        painter = QtGui.QPainter(pixmap)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        painter.setPen(self._pen_thumbnail())
        painter.setTransform(self._thumbnail_transform(size))
        painter.drawPath(self._symbol)
        painter.end()
        return pixmap


class QPointRoi(QPointRoiBase):
    changed = Signal(QtCore.QPointF)

    def __init__(self, x: float, y: float, parent=None):
        super().__init__(parent)
        self._point = QtCore.QPointF(x, y)

    def point(self) -> QtCore.QPointF:
        return self._point

    def _iter_points(self) -> Iterator[QtCore.QPointF]:
        yield self._point

    def setPoint(self, point: QtCore.QPointF):
        self._point = point
        self.changed.emit(self._point)

    def toRoi(self, indices) -> roi.PointRoi:
        return roi.PointRoi(
            x=self._point.x(), y=self._point.y(), indices=indices, name=self.label()
        )

    def translate(self, dx: float, dy: float):
        self.setPoint(QtCore.QPointF(self._point.x() + dx, self._point.y() + dy))

    def boundingRect(self) -> QtCore.QRectF:
        return QtCore.QRectF(
            self._point.x() - self._size,
            self._point.y() - self._size,
            self._size * 2,
            self._size * 2,
        )

    def _roi_type(self) -> str:
        return "point"


class QPointsRoi(QPointRoiBase):
    changed = Signal(list)

    def __init__(self, xs: Iterable[float], ys: Iterable[float], parent=None):
        super().__init__(parent)
        self._points = [QtCore.QPointF(x, y) for x, y in zip(xs, ys)]

    def count(self) -> int:
        return len(self._points)

    def pointAt(self, idx: int) -> QtCore.QPointF:
        return self._points[idx]

    def update_point(self, idx: int, pos: QtCore.QPointF):
        self._points[idx] = pos
        self.changed.emit(self._points)
        self._bounding_rect_cache = None

    def toRoi(self, indices) -> roi.PointsRoi:
        xs: list[float] = []
        ys: list[float] = []
        for point in self._points:
            xs.append(point.x())
            ys.append(point.y())
        return roi.PointsRoi(
            xs=np.array(xs), ys=np.array(ys), indices=indices, name=self.label()
        )

    def translate(self, dx: float, dy: float):
        self._points = [
            QtCore.QPointF(point.x() + dx, point.y() + dy) for point in self._points
        ]
        self.changed.emit(self._points)
        self._bounding_rect_cache = self._bounding_rect_cache.translated(dx, dy)

    def add_point(self, pos: QtCore.QPointF):
        self._points.append(pos)
        self.changed.emit(self._points)
        self._bounding_rect_cache = None

    def boundingRect(self) -> QtCore.QRectF:
        if self._bounding_rect_cache is None:
            xmin = np.min([pt.x() for pt in self._points])
            xmax = np.max([pt.x() for pt in self._points])
            ymin = np.min([pt.y() for pt in self._points])
            ymax = np.max([pt.y() for pt in self._points])
            self._bounding_rect_cache = QtCore.QRectF(
                xmin - self._size / 2,
                ymin - self._size / 2,
                xmax - xmin + self._size,
                ymax - ymin + self._size,
            )
        return self._bounding_rect_cache

    def _iter_points(self) -> Iterator[QtCore.QPointF]:
        yield from self._points

    def _roi_type(self) -> str:
        return "points"
