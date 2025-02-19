from __future__ import annotations
from contextlib import contextmanager
import math
from enum import Enum, auto
from qtpy import QtWidgets as QtW, QtCore, QtGui
from psygnal import Signal
import numpy as np
from typing import Iterable, Iterator, TYPE_CHECKING

from himena.standards import roi

if TYPE_CHECKING:
    from typing import Self


class QRoi(QtW.QGraphicsItem):
    """The base class for all ROI items."""

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {self.label()!r} at {hex(id(self))}>"

    def label(self) -> str:
        return getattr(self, "_roi_label", "")

    def set_label(self, label: str):
        self._roi_label = label

    def toRoi(self) -> roi.RoiModel:
        raise NotImplementedError

    def translate(self, dx: float, dy: float):
        raise NotImplementedError

    def makeThumbnail(self, pixmap: QtGui.QPixmap) -> QtGui.QPixmap:
        raise NotImplementedError

    def withPen(self, pen: QtGui.QPen):
        self.setPen(pen)
        return self

    def withLabel(self, label: str | None):
        self.set_label(label or "")
        return self

    def copy(self) -> Self:
        raise NotImplementedError("Subclasses must implement this method.")

    def _thumbnail_transform(self, width: int, height: int) -> QtGui.QTransform:
        rect = self.boundingRect()
        transform = QtGui.QTransform()
        rect_size = max(rect.width(), rect.height())
        if rect_size == 0:
            rect_size = 1
        transform.translate(width / 2, height / 2)
        transform.scale((width - 2) / rect_size, (height - 2) / rect_size)
        transform.translate(-rect.center().x(), -rect.center().y())
        return transform

    def _roi_type(self) -> str:
        return self.__class__.__name__

    def short_description(self, xscale: float, yscale: float, unit: str) -> str:
        """Description that will be shown in the status bar when the ROI is drawn."""
        return ""


class QLineRoi(QtW.QGraphicsLineItem, QRoi):
    changed = Signal(QtCore.QLineF)

    def toRoi(self) -> roi.LineRoi:
        x1, y1, x2, y2 = self._coordinates()
        return roi.LineRoi(
            x1=x1 - 0.5,
            y1=y1 - 0.5,
            x2=x2 - 0.5,
            y2=y2 - 0.5,
            name=self.label(),
        )

    def _coordinates(self) -> tuple[float, float, float, float]:
        line = self.line()
        return line.x1(), line.y1(), line.x2(), line.y2()

    def translate(self, dx: float, dy: float):
        new_line = self.line()
        new_line.translate(dx, dy)
        self.setLine(new_line)

    def setLine(self, *args):
        super().setLine(*args)
        self.changed.emit(self.line())

    def makeThumbnail(self, pixmap: QtGui.QPixmap) -> QtGui.QPixmap:
        painter = QtGui.QPainter(pixmap)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        painter.setPen(self.pen())
        painter.setTransform(self._thumbnail_transform(pixmap.width(), pixmap.height()))
        painter.drawLine(self.line())
        painter.end()
        return pixmap

    def copy(self) -> QLineRoi:
        return QLineRoi(self.line()).withPen(self.pen())

    def _roi_type(self) -> str:
        return "line"

    def short_description(self, xscale: float, yscale: float, unit: str) -> str:
        x1, y1, x2, y2 = self._coordinates()
        start = f"{x1:.1f}, {y1:.1f}"
        end = f"{x2:.1f}, {y2:.1f}"
        length_px = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
        length = math.sqrt(((x2 - x1) * xscale) ** 2 + ((y2 - y1) * yscale) ** 2)
        if not unit:
            return f"start=({start}), end=({end}), length={length_px:.1f}"
        return f"start=({start}), end=({end}), length={length_px:.1f} px ({length:.1f} {unit})"


class QRectRoiBase(QRoi):
    changed = Signal(QtCore.QRectF)


class QRectangleRoi(QtW.QGraphicsRectItem, QRectRoiBase):
    def toRoi(self) -> roi.RectangleRoi:
        rect = self.rect()
        return roi.RectangleRoi(
            x=rect.x(),
            y=rect.y(),
            width=rect.width(),
            height=rect.height(),
            name=self.label(),
        )

    def setRect(self, *args):
        super().setRect(*args)
        self.changed.emit(self.rect())

    def translate(self, dx: float, dy: float):
        new_rect = self.rect()
        new_rect.translate(dx, dy)
        self.setRect(new_rect)

    def makeThumbnail(self, pixmap: QtGui.QPixmap) -> QtGui.QPixmap:
        painter = QtGui.QPainter(pixmap)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        painter.setPen(self.pen())
        painter.setTransform(self._thumbnail_transform(pixmap.width(), pixmap.height()))
        painter.drawRect(self.rect())
        painter.end()
        return pixmap

    def copy(self) -> QRectangleRoi:
        return QRectangleRoi(self.rect()).withPen(self.pen())

    def _roi_type(self) -> str:
        return "rectangle"

    def short_description(self, xscale: float, yscale: float, unit: str) -> str:
        rect = self.rect()
        x, y, w, h = rect.x(), rect.y(), rect.width(), rect.height()
        width_px = w
        height_px = h
        width = w * xscale
        height = h * yscale
        if not unit:
            return f"left={x:.1f}, top={y:.1f}, width={width_px:.1f}, height={height_px:.1f}"
        return f"left={x:.1f}, top={y:.1f}, width={width_px:.1f} ({width:.1f} {unit}), height={height_px:.1f} ({height:.1f} {unit})"


class QEllipseRoi(QtW.QGraphicsEllipseItem, QRectRoiBase):
    changed = Signal(QtCore.QRectF)

    def toRoi(self) -> roi.EllipseRoi:
        rect = self.rect()
        return roi.EllipseRoi(
            x=rect.x(),
            y=rect.y(),
            width=rect.width(),
            height=rect.height(),
            name=self.label(),
        )

    def setRect(self, *args):
        super().setRect(*args)
        self.changed.emit(self.rect())

    def translate(self, dx: float, dy: float):
        new_rect = self.rect()
        new_rect.translate(dx, dy)
        self.setRect(new_rect)

    def makeThumbnail(self, pixmap: QtGui.QPixmap) -> QtGui.QPixmap:
        painter = QtGui.QPainter(pixmap)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        painter.setPen(self.pen())
        painter.setTransform(self._thumbnail_transform(pixmap.width(), pixmap.height()))
        painter.drawEllipse(self.rect())
        painter.end()
        return pixmap

    def copy(self) -> QEllipseRoi:
        return QEllipseRoi(self.rect()).withPen(self.pen())

    def _roi_type(self) -> str:
        return "ellipse"

    def short_description(self, xscale: float, yscale: float, unit: str) -> str:
        rect = self.rect()
        x, y, w, h = rect.x(), rect.y(), rect.width(), rect.height()
        cx = x + w / 2
        cy = y + h / 2
        width = w * xscale
        height = h * yscale
        if w == 0 or h == 0:
            eccentricity = "n.a."
        elif w < h:
            eccentricity = format(math.sqrt(1 - (width / height) ** 2), ".2f")
        else:
            eccentricity = format(math.sqrt(1 - (height / width) ** 2), ".2f")
        if not unit:
            return f"center=[{cx:.1f}, {cy:.1f}], width={w:.1f}, height={h:.1f}, eccentricity={eccentricity}"
        return f"center=[{cx:.1f}, {cy:.1f}], width={w:.1f} ({width:.1f} {unit}), height={h:.1f} ({height:.1f} {unit}), eccentricity={eccentricity}"


class QRotatedRectangleRoi(QRoi):
    changed = Signal(object)

    def __init__(self, start: QtCore.QPointF, end: QtCore.QPointF, width: float = 50):
        super().__init__()
        dr = end - start
        length = math.sqrt(dr.x() ** 2 + dr.y() ** 2)
        center = (start + end) / 2
        rad = math.atan2(dr.y(), dr.x())
        self._center = center
        self._angle = math.degrees(rad)
        self._length = length
        self._width = width
        self._pen = QtGui.QPen()
        self.set_start(start)
        self.set_end(end)

    def vector_x(self) -> QtCore.QPointF:
        rad = math.radians(self.angle())
        return QtCore.QPointF(math.cos(rad), math.sin(rad)) * self._length

    def vector_y(self) -> QtCore.QPointF:
        rad = math.radians(self.angle())
        return QtCore.QPointF(-math.sin(rad), math.cos(rad)) * self._width

    def angle(self) -> float:
        return self._angle

    def start(self) -> QtCore.QPointF:
        """Return the left anchor point."""
        return self._center - self.vector_x() / 2

    def end(self) -> QtCore.QPointF:
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

    def set_start(self, left: QtCore.QPointF):
        right = self.end()
        vecx = right - left
        with self._update_and_emit():
            self._angle = math.degrees(math.atan2(vecx.y(), vecx.x()))
            self._length = math.sqrt(vecx.x() ** 2 + vecx.y() ** 2)
            self._center = (left + right) / 2

    def set_end(self, right: QtCore.QPointF):
        left = self.start()
        vecx = right - left
        with self._update_and_emit():
            self._angle = math.degrees(math.atan2(vecx.y(), vecx.x()))
            self._length = math.sqrt(vecx.x() ** 2 + vecx.y() ** 2)
            self._center = (left + right) / 2

    def set_width(self, width: float):
        with self._update_and_emit():
            self._width = width

    def toRoi(self) -> roi.RotatedRectangleRoi:
        return roi.RotatedRectangleRoi(
            start=(self.start().x() - 0.5, self.start().y() - 0.5),
            end=(self.end().x() - 0.5, self.end().y() - 0.5),
            width=self._width,
            name=self.label(),
        )

    def pen(self) -> QtGui.QPen:
        return self._pen

    def setPen(self, pen: QtGui.QPen):
        self._pen = QtGui.QPen(pen)
        self.update()

    def translate(self, dx: float, dy: float):
        with self._update_and_emit():
            self._center += QtCore.QPointF(dx, dy)

    def copy(self) -> QRotatedRectangleRoi:
        return QRotatedRectangleRoi(self.start(), self.end(), self._width).withPen(
            self.pen()
        )

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

    def contains(self, point: QtCore.QPointF) -> bool:
        polygon = QtGui.QPolygonF(self._corner_points())
        return polygon.containsPoint(point, QtCore.Qt.FillRule.WindingFill)

    def makeThumbnail(self, pixmap: QtGui.QPixmap) -> QtGui.QPixmap:
        painter = QtGui.QPainter(pixmap)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        painter.setPen(self.pen())
        painter.setTransform(self._thumbnail_transform(pixmap.width(), pixmap.height()))
        painter.drawPolygon(*self._corner_points())
        painter.end()
        return pixmap

    def _roi_type(self) -> str:
        return "rotated rectangle"

    def short_description(self, xscale: float, yscale: float, unit: str) -> str:
        start = self.start()
        end = self.end()
        length_px = self._length
        length = length_px * xscale
        if not unit:
            return f"start=[{start.x():.1f}, {start.y():.1f}], end=[{end.x():.1f}, {end.y():.1f}], length={length_px:.1f}"
        return f"start=[{start.x():.1f}, {start.y():.1f}], end=[{end.x():.1f}, {end.y():.1f}], length={length_px:.1f} ({length:.1f} {unit})"


class QSegmentedLineRoi(QtW.QGraphicsPathItem, QRoi):
    changed = Signal(QtGui.QPainterPath)

    def __init__(self, xs: Iterable[float], ys: Iterable[float], parent=None):
        super().__init__(parent)
        path = QtGui.QPainterPath()
        path.moveTo(xs[0], ys[0])
        for x, y in zip(xs[1:], ys[1:]):
            path.lineTo(x, y)
        self.setPath(path)

    def toRoi(self) -> roi.SegmentedLineRoi:
        path = self.path()
        xs, ys = [], []
        for i in range(path.elementCount()):
            element = path.elementAt(i)
            xs.append(element.x - 0.5)
            ys.append(element.y - 0.5)
        return roi.SegmentedLineRoi(xs=xs, ys=ys, name=self.label())

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

    def makeThumbnail(self, pixmap: QtGui.QPixmap) -> QtGui.QPixmap:
        painter = QtGui.QPainter(pixmap)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        painter.setPen(self.pen())
        painter.setTransform(self._thumbnail_transform(pixmap.width(), pixmap.height()))
        painter.drawPath(self.path())
        painter.end()
        return pixmap

    def copy(self) -> QSegmentedLineRoi:
        path = self.path()
        xs, ys = [], []
        for i in range(path.elementCount()):
            element = path.elementAt(i)
            xs.append(element.x)
            ys.append(element.y)
        return QSegmentedLineRoi(xs, ys).withPen(self.pen())

    def _roi_type(self) -> str:
        return "segmented line"


class QPolygonRoi(QSegmentedLineRoi):
    def toRoi(self) -> roi.PolygonRoi:
        path = self.path()
        xs, ys = [], []
        closed = path.elementAt(0) == path.elementAt(path.elementCount() - 1)
        for i in range(path.elementCount() - int(closed)):
            element = path.elementAt(i)
            xs.append(element.x - 0.5)
            ys.append(element.y - 0.5)
        return roi.PolygonRoi(xs=xs, ys=ys, name=self.label())

    def _roi_type(self) -> str:
        return "polygon"


class QPointRoiBase(QRoi):
    def __init__(self, parent):
        super().__init__(parent)
        self._pen = QtGui.QPen(QtGui.QColor(0, 0, 0), 2)
        self._pen.setCosmetic(True)
        self._pen.setJoinStyle(QtCore.Qt.PenJoinStyle.MiterJoin)
        self._brush = QtGui.QBrush(QtGui.QColor(225, 225, 0))
        self._size = 4.5
        symbol = QtGui.QPainterPath()
        symbol.moveTo(-self._size, 0)
        symbol.lineTo(self._size, 0)
        symbol.moveTo(0, -self._size)
        symbol.lineTo(0, self._size)
        self._symbol = symbol
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

    def _repr_points(self) -> Iterable[tuple[float, float]]:
        """Return a list of (x, y) coordinates for drawing thumbnails."""
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

    def makeThumbnail(self, pixmap: QtGui.QPixmap) -> QtGui.QPixmap:
        painter = QtGui.QPainter(pixmap)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        painter.setPen(self.pen())
        for rx, ry in self._repr_points():
            painter.resetTransform()
            painter.translate(QtCore.QPointF(pixmap.width() * rx, pixmap.height() * ry))
            painter.scale(0.3, 0.3)
            painter.drawPath(self._symbol)
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

    def toRoi(self) -> roi.PointRoi2D:
        return roi.PointRoi2D(
            x=self._point.x() - 0.5,
            y=self._point.y() - 0.5,
            name=self.label(),
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

    def copy(self) -> QPointRoi:
        return QPointRoi(self._point.x(), self._point.y()).withPen(self.pen())

    def _roi_type(self) -> str:
        return "point"

    def _repr_points(self):
        return [(0.5, 0.5)]


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

    def toRoi(self) -> roi.PointsRoi2D:
        xs: list[float] = []
        ys: list[float] = []
        for point in self._points:
            xs.append(point.x() - 0.5)
            ys.append(point.y() - 0.5)
        return roi.PointsRoi2D(xs=np.array(xs), ys=np.array(ys), name=self.label())

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

    def copy(self) -> QPointsRoi:
        return QPointsRoi(
            [pt.x() for pt in self._points], [pt.y() for pt in self._points]
        ).withPen(self.pen())

    def _roi_type(self) -> str:
        return "points"

    def _repr_points(self):
        return [(0.2, 0.2), (0.5, 0.8), (0.8, 0.6)]


class MouseMode(Enum):
    """Mouse interaction modes for the image graphics view."""

    SELECT = auto()
    PAN_ZOOM = auto()
    ROI_RECTANGLE = auto()
    ROI_ROTATED_RECTANGLE = auto()
    ROI_ELLIPSE = auto()
    ROI_POINT = auto()
    ROI_POINTS = auto()
    ROI_POLYGON = auto()
    ROI_SEGMENTED_LINE = auto()
    ROI_LINE = auto()


SIMPLE_ROI_MODES = frozenset({
    MouseMode.ROI_RECTANGLE,
    MouseMode.ROI_ROTATED_RECTANGLE,
    MouseMode.ROI_ELLIPSE,
    MouseMode.ROI_POINT,
    MouseMode.ROI_LINE
})  # fmt: skip
MULTIPOINT_ROI_MODES = frozenset({
    MouseMode.ROI_POINTS, MouseMode.ROI_POLYGON, MouseMode.ROI_SEGMENTED_LINE
})  # fmt: skip
ROI_MODES = SIMPLE_ROI_MODES | MULTIPOINT_ROI_MODES
MULTIPOINT_ROI_CLASSES = (QPolygonRoi, QSegmentedLineRoi, QPointsRoi)
