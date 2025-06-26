from __future__ import annotations

from typing import TYPE_CHECKING, Literal
import numpy as np
from psygnal import Signal
from qtpy import QtCore, QtGui, QtWidgets as QtW
from ._base import QBaseGraphicsScene, QBaseGraphicsView
from himena.qt._qlineedit import QDoubleLineEdit
from himena_builtins.qt.widgets._shared import quick_min_max

if TYPE_CHECKING:
    from numpy import ndarray as NDArray


class QHistogramView(QBaseGraphicsView):
    """Graphics view for displaying histograms and setting contrast limits."""

    clim_changed = QtCore.Signal(tuple)

    def __init__(self):
        super().__init__()
        self._hist_items = [self.addItem(QHistogramItem())]
        self._line_low = self.addItem(QClimLineItem(0))
        self._line_high = self.addItem(QClimLineItem(1))
        self._line_low.valueChanged.connect(self._on_clim_changed)
        self._line_high.valueChanged.connect(self._on_clim_changed)
        self._view_range: tuple[float, float] = (0.0, 1.0)
        self._minmax = (0.0, 1.0)  # limits of the movable range
        self._pos_drag_start: QtCore.QPoint | None = None
        self._default_hist_scale = "linear"

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
        is_rgb: bool = False,
        color: QtGui.QColor = QtGui.QColor(100, 100, 100),
    ):
        # coerce the number of histogram items
        n_hist = 3 if is_rgb else 1
        for _ in range(n_hist, len(self._hist_items)):
            self.scene().removeItem(self._hist_items[-1])
            self._hist_items.pop()
        for _ in range(len(self._hist_items), n_hist):
            hist_item = QHistogramItem().with_hist_scale_func(self._default_hist_scale)
            self._hist_items.append(self.addItem(hist_item))

        minmax_fallback = clim
        if is_rgb:
            brushes = [
                QtGui.QBrush(QtGui.QColor(255, 0, 0, 128)),
                QtGui.QBrush(QtGui.QColor(0, 255, 0, 128)),
                QtGui.QBrush(QtGui.QColor(0, 0, 255, 255)),
            ]  # RGB
            for i, (item, brush) in enumerate(zip(self._hist_items, brushes)):
                item.with_brush(brush)
                item.set_hist_for_array(arr[:, :, i])
        else:
            brushes = [QtGui.QBrush(color)]
            self._hist_items[0].with_brush(brushes[0])
            # this fallback is needed when slider is changed.
            minmax_fallback = self._hist_items[0].set_hist_for_array(arr)

        if arr.dtype.kind in "ui":
            self.set_minmax((np.iinfo(arr.dtype).min, np.iinfo(arr.dtype).max))
        elif arr.dtype.kind == "b":
            self.set_minmax((0, 1))
        else:
            self.set_minmax(minmax_fallback)
        self.set_clim(clim)
        if self._view_range is None:
            self._view_range = clim

    def setValueFormat(self, fmt: str):
        self._line_low.setValueFormat(fmt)
        self._line_high.setValueFormat(fmt)

    def viewRect(self, width: float | None = None) -> QtCore.QRectF:
        """The current view range as a QRectF."""
        x0, x1 = self._view_range
        if width is None:
            width = x1 - x0
        return QtCore.QRectF(x0 - width * 0.03, 0, width * 1.06, 1)

    def set_view_range(self, x0: float, x1: float):
        self._view_range = (x0, x1)
        self.fitInView(self.viewRect(), QtCore.Qt.AspectRatioMode.IgnoreAspectRatio)

    def resizeEvent(self, event: QtGui.QResizeEvent):
        super().resizeEvent(event)
        self.fitInView(self.viewRect(), QtCore.Qt.AspectRatioMode.IgnoreAspectRatio)

    def showEvent(self, event: QtGui.QShowEvent):
        super().showEvent(event)
        x0, x1 = self.clim()
        self.fitInView(
            self.viewRect(x1 - x0), QtCore.Qt.AspectRatioMode.IgnoreAspectRatio
        )
        self._line_low.setValue(self._line_low.value())
        self._line_high.setValue(self._line_high.value())

    def mouseDoubleClickEvent(self, event: QtGui.QMouseEvent):
        self._reset_view()

    def _reset_view(self):
        rect = self._line_low.boundingRect().united(self._line_high.boundingRect())
        for hist in self._hist_items:
            rect = rect.united(hist.boundingRect())
        x0, x1 = rect.left(), rect.right()
        self.fitInView(
            self.viewRect(x1 - x0), QtCore.Qt.AspectRatioMode.IgnoreAspectRatio
        )
        self._view_range = (x0, x1)

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
        self.set_view_range(x0, x1)

    def mousePressEvent(self, event: QtGui.QMouseEvent):
        self._pos_drag_start = event.pos()
        self._pos_drag_prev = self._pos_drag_start
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QtGui.QMouseEvent):
        if self.scene().grabSource():
            return super().mouseMoveEvent(event)
        if event.buttons() & QtCore.Qt.MouseButton.LeftButton:
            pos = event.pos()
            if self._pos_drag_prev is not None:
                delta = self.mapToScene(pos) - self.mapToScene(self._pos_drag_prev)
                delta = delta.x()
                x0, x1 = self._view_range
                x0 -= delta
                x1 -= delta
                self.set_view_range(x0, x1)
            self._pos_drag_prev = pos
        return super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent):
        if (
            event.button() == QtCore.Qt.MouseButton.RightButton
            and self._pos_drag_start is not None
            and (self._pos_drag_start - event.pos()).manhattanLength() < 8
        ):
            # right clicked
            menu = self._make_context_menu()
            menu.exec(self.mapToGlobal(event.pos()))

        self._pos_drag_start = None
        self._pos_drag_prev = None
        self.scene().setGrabSource(None)
        return super().mouseReleaseEvent(event)

    def _make_context_menu(self) -> QtW.QMenu:
        menu = QtW.QMenu(self)
        menu.addAction("Reset view", self._reset_view)
        menu_scale = menu.addMenu("Scale")
        for scale in ["linear", "log"]:
            ac = menu_scale.addAction(
                scale.title(), lambda s=scale: self._set_hist_scale_func(s)
            )
            ac.setCheckable(True)
            ac.setChecked(scale == self._default_hist_scale)
        menu.addSeparator()
        menu.addAction("Copy Histogram", self._img_to_clipboard)
        return menu

    def _set_hist_scale_func(self, scale: Literal["linear", "log"]):
        for hist in self._hist_items:
            hist.with_hist_scale_func(scale)
        self._default_hist_scale = scale

    def _img_to_clipboard(self):
        img = self.grab().toImage()
        QtW.QApplication.clipboard().setImage(img)


class QClimLineItem(QtW.QGraphicsRectItem):
    """The line item for one of the contrast limits."""

    # NOTE: To properly set the bounding rect, we need to inherit from QGraphicsRectItem
    # with updated boundingRect method.
    valueChanged = Signal(float)
    _Y_LOW = -1
    _Y_HIGH = 2
    _WIDTH_NORMAL = 2
    _WIDTH_HOVER = 4

    def __init__(self, x: float):
        super().__init__()
        self._color = QtGui.QColor(255, 0, 0, 150)
        pen = QtGui.QPen(self._color, self._WIDTH_NORMAL)
        pen.setCosmetic(True)
        self._qpen = pen
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
        self.setAcceptHoverEvents(True)

    def mousePressEvent(self, event: QtW.QGraphicsSceneMouseEvent):
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self._is_dragging = True
            self.scene().setGrabSource(self)
        elif event.buttons() & QtCore.Qt.MouseButton.RightButton:
            self.scene().setGrabSource(self)
            menu = QClimMenu(self.scene().views()[0], self)
            menu._edit.setFocus()
            menu.exec(event.screenPos())
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QtW.QGraphicsSceneMouseEvent):
        if event.buttons() & QtCore.Qt.MouseButton.LeftButton:
            if self._is_dragging:
                self._drag_event(event)

    def mouseReleaseEvent(self, event: QtW.QGraphicsSceneMouseEvent):
        self._is_dragging = False
        self.scene().setGrabSource(None)
        self.setValue(event.pos().x())
        return super().mouseReleaseEvent(event)

    def hoverEnterEvent(self, event):
        self._qpen.setWidthF(self._WIDTH_HOVER)
        self._show_value_label()
        self.update()
        return super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self._qpen.setWidthF(self._WIDTH_NORMAL)
        self._value_label.hide()
        self.update()
        return super().hoverLeaveEvent(event)

    def _show_value_label(self):
        txt = format(self.value(), self._value_fmt)
        self._value_label.setText(txt)
        vp = self.scene().views()[0].viewport()
        background_color = vp.palette().color(vp.backgroundRole())

        brightness = (
            0.299 * background_color.red()
            + 0.587 * background_color.green()
            + 0.114 * background_color.blue()
        )
        if brightness > 127:
            self._value_label.setBrush(QtGui.QBrush(QtCore.Qt.GlobalColor.black))
        else:
            self._value_label.setBrush(QtGui.QBrush(QtCore.Qt.GlobalColor.white))
        text_width = self._value_label.boundingRect().width()
        pos = QtCore.QPointF(self.value(), 0)
        if pos.x() + text_width / self._x_scale() > self._range[1]:
            pos.setX(pos.x() - (text_width + 4) / self._x_scale())
        else:
            pos.setX(pos.x() + 4 / self._x_scale())
        self._value_label.setPos(self.mapToScene(pos))
        if self._value_label.scene() is None:
            # prevent scene movement during adding the label
            rect = self.scene().sceneRect()
            self.scene().addItem(self._value_label)
            self.scene().setSceneRect(rect)
        self._value_label.show()

    def _drag_event(self, event: QtW.QGraphicsSceneMouseEvent):
        self.setValue(event.pos().x())
        self._show_value_label()
        if scene := self.scene():
            scene.update()

    def setValueFormat(self, fmt: str):
        self._value_fmt = fmt

    def paint(self, painter, option, widget):
        painter.setPen(self._qpen)
        start = QtCore.QPointF(self._value, self._Y_LOW)
        end = QtCore.QPointF(self._value, self._Y_HIGH)
        line = QtCore.QLineF(start, end)
        painter.drawLine(line)

    def value(self) -> float:
        """The x value of the line (the contrast limit)."""
        return self._value

    def setValue(self, x: float):
        """Set the x value of the line (the contrast limit)."""
        old_bbox = self.boundingRect()
        old_value = self._value
        new_value = min(max(x, self._range[0]), self._range[1])
        self._value = new_value
        new_bbox = self.boundingRect()
        self.setRect(new_bbox)
        if new_value != old_value:
            self.valueChanged.emit(self._value)
        if scene := self.scene():
            scene.update(self.mapRectToScene(old_bbox.united(new_bbox)))

    def setRange(self, low: float, high: float):
        """Set the min/max range of the line x value."""
        self._range = (low, high)
        if not low <= self.value() <= high:
            self.setValue(self.value())

    def scene(self) -> QBaseGraphicsScene:
        return super().scene()

    def _x_scale(self) -> float:
        return self.view().transform().m11()

    def view(self) -> QHistogramView:
        return self.scene().views()[0]

    def boundingRect(self):
        w = 10.0 / self._x_scale()
        x = self.value()
        return QtCore.QRectF(x - w / 2, self._Y_LOW, w, self._Y_HIGH - self._Y_LOW)


class QHistogramItem(QtW.QGraphicsPathItem):
    def __init__(self):
        super().__init__()
        self._hist_path = QtGui.QPainterPath()
        self._hist_brush = QtGui.QBrush(QtGui.QColor(100, 100, 100))
        self.setPen(QtGui.QPen(QtGui.QColor(0, 0, 0, 0)))
        self._edges = np.array([0.0, 1.0])
        self._hist_values = np.zeros(0)
        self._hist_scale_func = _linear_scale

    def with_brush(self, brush: QtGui.QBrush) -> QHistogramItem:
        self._hist_brush = brush
        return self

    def with_hist_scale_func(self, scale: Literal["linear", "log"]) -> QHistogramItem:
        if scale == "linear":
            self._hist_scale_func = _linear_scale
        elif scale == "log":
            self._hist_scale_func = _log_scale
        else:
            raise ValueError(f"Unknown histogram scale: {scale}")
        self._update_histogram_path()
        return self

    def set_hist_for_array(self, arr: NDArray[np.number]) -> tuple[float, float]:
        _min, _max = quick_min_max(arr)
        if arr.dtype in ("int8", "uint8"):
            _nbin = 64
        else:
            _nbin = 256
        _nbin = min(_nbin, int(np.prod(arr.shape[-2:])) // 2)
        # draw histogram
        if arr.dtype.kind == "b":
            edges = np.array([0, 0.5, 1])
            frac_true = np.sum(arr) / arr.size
            hist = np.array([1 - frac_true, frac_true])
        elif _max > _min:
            arr = arr.clip(_min, _max)
            if arr.dtype.kind in "ui" and _max - _min < _nbin:
                # bin number is excessive
                _nbin = int(_max - _min)
                normed = (arr - _min).astype(np.uint8)
            else:
                normed = ((arr - _min) / (_max - _min) * _nbin).astype(np.uint8)
            hist = np.bincount(normed.ravel(), minlength=_nbin)
            edges = np.linspace(_min, _max, _nbin + 1)
        else:
            edges = np.array([_min, _max])
            hist = np.zeros(1)
        self._edges = edges
        self._hist_values = hist

        self._update_histogram_path()
        return _min, _max

    def _update_histogram_path(self):
        _path = QtGui.QPainterPath()
        edges = self._edges
        hist = self._hist_values
        self.setBrush(self._hist_brush)
        _path.moveTo(edges[0], 1)
        for e0, e1, h in zip(edges[:-1], edges[1:], self._hist_scale_func(hist)):
            _path.lineTo(e0, 1 - h)
            _path.lineTo(e1, 1 - h)
        _path.lineTo(edges[-1], 1)
        _path.closeSubpath()
        self.setPath(_path)
        self.update()


def _linear_scale(hist: NDArray[np.number]) -> NDArray[np.number]:
    if hist.size > 0 and (hmax := hist.max()) > 0:
        return hist / hmax
    return hist


def _log_scale(hist: NDArray[np.number]) -> NDArray[np.number]:
    hist_log = np.log(hist + 1)
    if hist_log.size > 0 and (hmax := hist_log.max()) > 0:
        return hist_log / hmax
    return hist_log


class QClimMenu(QtW.QMenu):
    def __init__(self, parent: QHistogramView, item: QClimLineItem):
        super().__init__(parent)
        self._hist_view = parent
        self._item = item
        self._edit = QDoubleLineEdit()
        self._edit.setText(format(item.value(), item._value_fmt))
        self._edit.editingFinished.connect(self._on_value_changed)
        widget_action = QtW.QWidgetAction(self)
        widget_action.setDefaultWidget(self._edit)
        self.addAction(widget_action)

    def _on_value_changed(self):
        value = float(self._edit.text())
        self._item.setValue(value)
        # update min/max
        if value < self._hist_view._minmax[0]:
            self._hist_view.set_minmax((value, self._hist_view._minmax[1]))
        elif value > self._hist_view._minmax[1]:
            self._hist_view.set_minmax((self._hist_view._minmax[0], value))
        # update view range
        v0, v1 = self._hist_view._view_range
        if value < v0:
            self._hist_view.set_view_range(value, v1)
        elif value > v1:
            self._hist_view.set_view_range(v0, value)
        self.close()
