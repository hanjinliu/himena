from __future__ import annotations

from typing import TYPE_CHECKING
import numpy as np
from psygnal import Signal
from qtpy import QtCore, QtGui, QtWidgets as QtW
from ._base import QBaseGraphicsScene, QBaseGraphicsView

if TYPE_CHECKING:
    from numpy import ndarray as NDArray


class QHistogramView(QBaseGraphicsView):
    clim_changed = QtCore.Signal(tuple)

    def __init__(self):
        super().__init__()
        self._hist_items = [self.addItem(QHistogramItem())]
        self._line_low = self.addItem(QClimLineItem(0))
        self._line_high = self.addItem(QClimLineItem(1))
        self._line_low.valueChanged.connect(self._on_clim_changed)
        self._line_high.valueChanged.connect(self._on_clim_changed)
        self._view_range: tuple[float, float] = (0.0, 1.0)
        self._minmax = (0.0, 1.0)
        self._pos_drag_start: QtCore.QPoint | None = None

    def _on_clim_changed(self):
        clim = self.clim()
        if self._view_range is not None:
            v0, v1 = self._view_range
            x0, x1 = self.clim()
            if x0 < v0 or x1 > v1:
                self._view_range = clim
                self.update()
        self.clim_changed.emit(clim)

    def clim(self) -> tuple[float, float]:
        return tuple(sorted([self._line_low.value(), self._line_high.value()]))

    def set_clim(self, clim: tuple[float, float]):
        self._line_low.setValue(max(clim[0], self._minmax[0]))
        self._line_high.setValue(min(clim[1], self._minmax[1]))

    def set_minmax(self, minmax: tuple[float, float]):
        self._minmax = minmax
        self._line_low.setRange(*minmax)
        self._line_high.setRange(*minmax)

    def set_hist_for_array(
        self,
        arr: NDArray[np.number],
        clim: tuple[float, float],
        minmax: tuple[float, float],
        is_rgb: bool = False,
    ):
        # coerce the number of histogram items
        n_hist = 3 if is_rgb else 1
        for _ in range(n_hist, len(self._hist_items)):
            self.scene().removeItem(self._hist_items[-1])
            self._hist_items.pop()
        for _ in range(len(self._hist_items), n_hist):
            self._hist_items.append(self.addItem(QHistogramItem()))

        if is_rgb:
            brushes = [
                QtGui.QBrush(QtGui.QColor(255, 0, 0, 128)),
                QtGui.QBrush(QtGui.QColor(0, 255, 0, 128)),
                QtGui.QBrush(QtGui.QColor(0, 0, 255, 255)),
            ]  # RGB
            for i, (item, brush) in enumerate(zip(self._hist_items, brushes)):
                item.with_brush(brush)
                item.set_hist_for_array(arr[:, :, i], minmax)
        else:
            brushes = [QtGui.QBrush(QtGui.QColor(100, 100, 100))]
            self._hist_items[0].with_brush(brushes[0])
            self._hist_items[0].set_hist_for_array(arr, minmax)

        self.set_minmax(minmax)
        self.set_clim(clim)
        if self._view_range is None:
            self._view_range = minmax

    def setValueFormat(self, fmt: str):
        self._line_low.setValueFormat(fmt)
        self._line_high.setValueFormat(fmt)

    def viewRect(self) -> QtCore.QRectF:
        """The current view range as a QRectF."""
        x0, x1 = self._view_range
        return QtCore.QRectF(x0, 0, x1 - x0, 1)

    def setViewRange(self, x0: float, x1: float):
        self._view_range = (x0, x1)
        self.fitInView(self.viewRect(), QtCore.Qt.AspectRatioMode.IgnoreAspectRatio)

    def resizeEvent(self, event: QtGui.QResizeEvent):
        super().resizeEvent(event)
        self.fitInView(self.viewRect(), QtCore.Qt.AspectRatioMode.IgnoreAspectRatio)

    def showEvent(self, event: QtGui.QShowEvent):
        super().showEvent(event)
        self.fitInView(self.viewRect(), QtCore.Qt.AspectRatioMode.IgnoreAspectRatio)

    def mouseDoubleClickEvent(self, event: QtGui.QMouseEvent):
        x0, x1 = self._minmax
        rect = QtCore.QRectF(x0, 0, x1 - x0, 1)
        self.fitInView(rect, QtCore.Qt.AspectRatioMode.IgnoreAspectRatio)

    def wheelEvent(self, event: QtGui.QWheelEvent):
        delta = event.angleDelta().y()
        if delta > 0:
            factor = 1.1
        else:
            factor = 1 / 1.1
        x0, x1 = self._view_range
        xcursor = self.mapToScene(event.pos()).x()
        x0 = max((x0 - xcursor) / factor + xcursor, self._minmax[0])
        x1 = min((x1 - xcursor) / factor + xcursor, self._minmax[1])
        self.setViewRange(x0, x1)

    def mousePressEvent(self, event: QtGui.QMouseEvent):
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self._pos_drag_start = event.pos()
            self._pos_drag_prev = self._pos_drag_start
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QtGui.QMouseEvent):
        if self.scene().grabSource():
            return super().mouseMoveEvent(event)
        if event.buttons() & QtCore.Qt.MouseButton.LeftButton:
            if self._pos_drag_prev is not None:
                delta = self.mapToScene(event.pos()) - self.mapToScene(
                    self._pos_drag_prev
                )
                delta = delta.x()
                x0, x1 = self._view_range
                if x0 - delta < self._minmax[0]:
                    delta = x0 - self._minmax[0]
                elif x1 - delta > self._minmax[1]:
                    delta = x1 - self._minmax[1]
                x0 -= delta
                x1 -= delta
                self.setViewRange(x0, x1)
            self._pos_drag_prev = event.pos()
        return super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent):
        self._pos_drag_start = None
        self._pos_drag_prev = None
        self.scene().setGrabSource(None)
        return super().mouseReleaseEvent(event)


class QClimLineItem(QtW.QGraphicsLineItem):
    valueChanged = Signal(float)
    _Y_LOW = -1
    _Y_HIGH = 2

    def __init__(self, x: float):
        super().__init__(x, self._Y_LOW, x, self._Y_HIGH)
        pen = QtGui.QPen(QtGui.QColor(255, 0, 0, 150), 4)
        pen.setCosmetic(True)
        self.setPen(pen)
        self.setZValue(1000)
        self.setFlag(QtW.QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self._is_dragging = False
        self._range = (-float("inf"), float("inf"))
        self._value = x
        self._value_fmt = ".1f"
        self.setCursor(QtCore.Qt.CursorShape.SizeHorCursor)
        self._value_label = QtW.QGraphicsSimpleTextItem()
        self._value_label.setFlag(
            QtW.QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations
        )
        self._value_label.setFont(QtGui.QFont("Arial", 8))

    def mousePressEvent(self, event: QtW.QGraphicsSceneMouseEvent):
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self._is_dragging = True
            self.scene().setGrabSource(self)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QtW.QGraphicsSceneMouseEvent):
        if event.buttons() & QtCore.Qt.MouseButton.LeftButton:
            if self._is_dragging:
                self._drag_event(event)
        self._show_value_label()

    def mouseReleaseEvent(self, event: QtW.QGraphicsSceneMouseEvent):
        self._is_dragging = False
        self._value_label.hide()
        self.scene().setGrabSource(None)
        return super().mouseReleaseEvent(event)

    def _show_value_label(self):
        txt = format(self.value(), self._value_fmt)
        if self._value_label.scene() is None:
            self.scene().addItem(self._value_label)
        self._value_label.setText(txt)
        pos = QtCore.QPointF(self.value(), 0)
        if pos.x() > self.scene().width() - 50:
            text_width = self._value_label.boundingRect().width()
            self._value_label.setPos(
                self.mapToScene(pos) + QtCore.QPointF(-5 - text_width, 0)
            )
        else:
            self._value_label.setPos(self.mapToScene(pos) + QtCore.QPointF(5, 0))
        self._value_label.show()

    def _drag_event(self, event: QtW.QGraphicsSceneMouseEvent):
        self.setValue(event.scenePos().x())
        self._show_value_label()

    def setValueFormat(self, fmt: str):
        self._value_fmt = fmt

    def value(self) -> float:
        """The x value of the line (the contrast limit)."""
        return self._value

    def setValue(self, x: float):
        """Set the x value of the line (the contrast limit)."""
        self._value = min(max(x, self._range[0]), self._range[1])
        super().setLine(self._value, self._Y_LOW, self._value, self._Y_HIGH)
        self.valueChanged.emit(self._value)

    def setRange(self, low: float, high: float):
        """Set the min/max range of the line x value."""
        self._range = (low, high)
        if not low <= self.value() <= high:
            self.setValue(self.value())

    def scene(self) -> QBaseGraphicsScene:
        return super().scene()


class QHistogramItem(QtW.QGraphicsPathItem):
    def __init__(self):
        super().__init__()
        self._hist_path = QtGui.QPainterPath()
        self._hist_brush = QtGui.QBrush(QtGui.QColor(100, 100, 100))
        self.setPen(QtGui.QPen(QtGui.QColor(0, 0, 0, 0)))

    def with_brush(self, brush: QtGui.QBrush) -> QHistogramItem:
        self._hist_brush = brush
        return self

    def set_hist_for_array(
        self,
        arr: NDArray[np.number],
        minmax: tuple[float, float],
    ):
        _min, _max = minmax
        if arr.dtype in ("uint8", "uint8"):
            _nbin = 64
        else:
            _nbin = 128
        # draw histogram
        if arr.dtype.kind == "b":
            edges = np.array([0, 1])
            frac_true = np.sum(arr) / arr.size
            hist = np.array([1 - frac_true, frac_true])
        elif _max > _min:
            normed = ((arr - _min) / (_max - _min) * _nbin).astype(np.uint8)
            hist = np.bincount(normed.ravel(), minlength=_nbin)
            hist = hist / hist.max()
            edges = np.linspace(_min, _max, _nbin + 1)
        else:
            edges = np.array([_min, _max])
            hist = np.zeros(1)
        _path = QtGui.QPainterPath()
        self.setBrush(self._hist_brush)
        _path.moveTo(edges[0], 1)
        for e0, e1, h in zip(edges[:-1], edges[1:], hist):
            _path.lineTo(e0, 1 - h)
            _path.lineTo(e1, 1 - h)
        _path.lineTo(edges[-1], 1)
        _path.closeSubpath()
        self.setPath(_path)
        self.update()
