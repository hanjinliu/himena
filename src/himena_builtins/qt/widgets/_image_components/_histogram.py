from __future__ import annotations

from typing import TYPE_CHECKING, Literal
import numpy as np
from psygnal import Signal
from qtpy import QtCore, QtGui, QtWidgets as QtW
from functools import reduce
from himena.consts import DefaultFontFamily
from ._base import QBaseGraphicsScene, QBaseGraphicsView
from himena.qt._qlineedit import QDoubleLineEdit
from himena_builtins.qt.widgets._shared import quick_min_max

if TYPE_CHECKING:
    from numpy.typing import NDArray


class QHistogramView(QBaseGraphicsView):
    """Graphics view for displaying histograms and setting contrast limits."""

    clim_changed = QtCore.Signal(tuple)
    threshold_changed = QtCore.Signal(float)

    def __init__(self, mode: Literal["clim", "thresh"] = "clim"):
        super().__init__()
        self._hist_items = [self.addItem(QHistogramItem())]
        self._qclim_set = ClimLineItemSet()
        self._qthresh_item = QClimLineItem(0)
        self.addItem(self._qclim_set._low)
        self.addItem(self._qclim_set._high)
        self.addItem(self._qclim_set._gamma_line)
        self.addItem(self._qthresh_item)
        if mode == "clim":
            self._qthresh_item.hide()
        else:
            self._qclim_set.hide()
        self._line_items = [
            self._qclim_set._low,
            self._qclim_set._high,
            self._qthresh_item,
        ]
        self._qclim_set.valueChanged.connect(self._on_clim_changed)
        self._qthresh_item.valueChanged.connect(self._on_thresh_changed)

        self._view_range: tuple[float, float] = (0.0, 1.0)
        self._minmax = (0.0, 1.0)  # limits of the movable range
        self._pos_drag_start = QtCore.QPoint()
        self._pos_drag_prev = QtCore.QPoint()
        self._default_hist_scale: Literal["linear", "log"] = "linear"

    def set_mode(self, mode: Literal["clim", "thresh"]):
        """Set the mode of the histogram view.

        Parameters
        ----------
        mode : Literal["clim", "thresh"]
            The mode to set. "clim" for contrast limits, "thresh" for threshold.
        """
        if mode == "clim":
            self._qthresh_item.hide()
            self._qclim_set.show()
            for item in self._line_items:
                item._show_value_label()
        else:
            self._qthresh_item.show()
            self._qclim_set.hide()

    def _on_clim_changed(self, clim):
        if self._view_range is not None:
            v0, v1 = self._view_range
            x0, x1 = clim
            if x0 < v0 or x1 > v1:
                self._view_range = clim
                self.update()
        self.clim_changed.emit(clim)

    def _on_thresh_changed(self, thresh):
        if self._view_range is not None:
            v0, v1 = self._view_range
            if thresh < v0 or thresh > v1:
                self._view_range = (min(v0, thresh), max(v1, thresh))
                self.update()
        self.threshold_changed.emit(thresh)

    def clim(self) -> tuple[float, float]:
        """Return the current contrast limits as (low, high)."""
        return self._qclim_set.clim()

    def set_clim(self, clim: tuple[float, float]):
        """Set the current contrast limits."""
        c0 = max(clim[0], self._minmax[0])
        c1 = min(clim[1], self._minmax[1])
        return self._qclim_set.set_clim((c0, c1))

    def threshold(self) -> float:
        """Return the current threshold value."""
        return self._qthresh_item.value()

    def set_threshold(self, thresh: float):
        """Set the current threshold value."""
        return self._qthresh_item.setValue(thresh)

    def set_minmax(self, minmax: tuple[float, float]):
        """Set the movable range of the line items."""
        self._minmax = minmax
        for line_item in self._line_items:
            line_item.setRange(*minmax)

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
                item.set_hist_for_array(arr[..., i])
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

    def setValueFormat(self, fmt: str, always_show: bool = False):
        """Set the format string for the line item value labels.

        Parameters
        ----------
        fmt : str
            The format string, e.g., ".2f" for two decimal places.
        always_show : bool
            If True, the value label is always shown. Otherwise, it is only shown on
            hover.
        """
        for line_item in self._line_items:
            line_item.setValueFormat(fmt, always_show)

    def viewRect(self, width: float | None = None) -> QtCore.QRectF:
        """The current view range as a QRectF."""
        x0, x1 = self._view_range
        if width is None:
            width = x1 - x0
        return QtCore.QRectF(x0 - width * 0.03, 0, width * 1.06, 1)

    def set_view_range(self, x0: float, x1: float):
        self._view_range = (x0, x1)
        self.fitInView(self.viewRect(), QtCore.Qt.AspectRatioMode.IgnoreAspectRatio)

    def calc_contrast_limits(
        self, qmin: float, qmax: float
    ) -> tuple[float, float] | None:
        """Calculate contrast limits based on the given quantiles."""
        min_new, max_new = float("inf"), -float("inf")
        for item in self._hist_items:
            cum_value = np.cumsum(item._hist_values)
            cum_value = np.concatenate([[0.0], cum_value / cum_value[-1]])
            min_new = min(_interp_hist(qmin, item._edges, cum_value), min_new)
            max_new = max(_interp_hist(qmax, item._edges, cum_value), max_new)
        if np.isinf(min_new) or np.isinf(max_new):
            return
        return min_new, max_new

    def resizeEvent(self, event: QtGui.QResizeEvent):
        super().resizeEvent(event)
        self.fitInView(self.viewRect(), QtCore.Qt.AspectRatioMode.IgnoreAspectRatio)

    def showEvent(self, event: QtGui.QShowEvent):
        super().showEvent(event)
        x0, x1 = self._view_range
        self.fitInView(
            self.viewRect(x1 - x0), QtCore.Qt.AspectRatioMode.IgnoreAspectRatio
        )
        # update line items
        for line_item in self._line_items:
            line_item.setValue(line_item.value())

    def mouseDoubleClickEvent(self, event: QtGui.QMouseEvent):
        self._reset_view()

    def _reset_view(self):
        # Unite all items' bounding rects
        rect = reduce(
            lambda a, b: a.united(b),
            (item.boundingRect() for item in self._line_items if item.isVisible()),
            QtCore.QRectF(),
        )

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
        self._pos_drag_prev = self._pos_drag_start = event.pos()
        return super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QtGui.QMouseEvent):
        if self.scene().grabSource():
            return super().mouseMoveEvent(event)
        if event.buttons() & QtCore.Qt.MouseButton.LeftButton:
            pos = event.pos()
            if not self._pos_drag_prev.isNull():
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
            and (not self._pos_drag_start.isNull())
            and (self._pos_drag_start - event.pos()).manhattanLength() < 8
        ):
            # right clicked
            menu = self._make_context_menu()
            menu.exec(self.mapToGlobal(event.pos()))

        self._pos_drag_start = QtCore.QPoint()
        self._pos_drag_prev = QtCore.QPoint()
        self.scene().setGrabSource(None)
        return super().mouseReleaseEvent(event)

    def _make_context_menu(self) -> QtW.QMenu:
        menu = QtW.QMenu(self)
        menu.addAction("Reset view", self._reset_view)
        menu_scale = menu.addMenu("Scale")
        for scale in ["linear", "log"]:
            ac = menu_scale.addAction(
                scale.title(), lambda s=scale: self.set_hist_scale(s)
            )
            ac.setCheckable(True)
            ac.setChecked(scale == self._default_hist_scale)
        menu.addSeparator()
        menu.addAction("Copy Histogram", self._img_to_clipboard)
        return menu

    def set_hist_scale(self, scale: Literal["linear", "log"]):
        for hist in self._hist_items:
            hist.with_hist_scale_func(scale)
        self._default_hist_scale = scale

    def _img_to_clipboard(self):
        img = self.grab().toImage()
        QtW.QApplication.clipboard().setImage(img)


class ClimLineItemSet(QtCore.QObject):
    valueChanged = Signal(tuple)

    def __init__(self):
        super().__init__()
        self._low = QClimLineItem(0)
        self._high = QClimLineItem(1)
        self._gamma_line = QtW.QGraphicsLineItem()
        pen = QtGui.QPen(self._low._color, 1)
        pen.setCosmetic(True)
        self._gamma_line.setPen(pen)
        self._low.valueChanged.connect(self._line_changed)
        self._high.valueChanged.connect(self._line_changed)

    def clim(self) -> tuple[float, float]:
        return tuple(sorted([self._low.value(), self._high.value()]))

    def set_clim(self, clim: tuple[float, float]):
        self._low.setValue(clim[0])
        self._high.setValue(clim[1])

    def _line_changed(self):
        clim = self.clim()
        self._gamma_line.setLine(clim[0], 1, clim[1], 0)
        self.valueChanged.emit(clim)

    def show(self):
        self._low.show()
        self._high.show()
        self._gamma_line.show()

    def hide(self):
        self._low.hide()
        self._high.hide()
        self._gamma_line.hide()


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
        self._value = float(x)
        self._value_fmt = ".1f"
        self.setCursor(QtCore.Qt.CursorShape.SizeHorCursor)
        self._value_label = QtW.QGraphicsSimpleTextItem(self)
        self._value_label.setFlag(
            QtW.QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations
        )
        self._value_label.setFont(QtGui.QFont(DefaultFontFamily, 8))
        self.setAcceptHoverEvents(True)
        self._always_show_value = False

    def mousePressEvent(self, event: QtW.QGraphicsSceneMouseEvent):
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self._is_dragging = True
            self.scene().setGrabSource(self)
        elif event.buttons() & QtCore.Qt.MouseButton.RightButton:
            self.scene().setGrabSource(self)
            if view := self.view():
                menu = QClimMenu(view, self)
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

    def view(self) -> QHistogramView | None:
        if scene := self.scene():
            views = scene.views()
            if len(views) > 0:
                return views[0]
        return None

    def hoverEnterEvent(self, event):
        self._qpen.setWidthF(self._WIDTH_HOVER)
        self._show_value_label()
        self.update()
        return super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self._qpen.setWidthF(self._WIDTH_NORMAL)
        if not self._always_show_value:
            self._value_label.hide()
        self.update()
        return super().hoverLeaveEvent(event)

    def _show_value_label(self):
        if not self.isVisible():
            return self.hide()
        txt = format(self.value(), self._value_fmt)
        self._value_label.setText(txt)
        if (view := self.view()) is None:
            return
        vp = view.viewport()
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

    def setValueFormat(self, fmt: str, always_show: bool = False):
        self._value_fmt = fmt
        self._always_show_value = always_show
        if always_show:
            self._show_value_label()
            if scene := self.scene():
                scene.update()

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
        self._value = float(new_value)
        new_bbox = self.boundingRect()
        self.setRect(new_bbox)
        if new_value != old_value:
            self.valueChanged.emit(self._value)
        if self._value_label.isVisible():
            self._show_value_label()
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
        if view := self.view():
            return view.transform().m11()
        return 1.0

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
        # nbin should not be more than half of the number of pixels
        _nbin = min(_nbin, int(arr.size) // 2)
        # draw histogram
        if arr.dtype.kind == "b":
            edges = np.array([0, 0.5, 1])
            frac_true = np.sum(arr) / arr.size
            hist = np.array([1 - frac_true, frac_true])
        elif _max > _min:
            arr = arr.clip(_min, _max)
            if arr.dtype.kind in "ui":
                _nbin = int(_max - _min) // max(int(np.ceil((_max - _min) / _nbin)), 1)
            normed = ((arr - _min) / (_max - _min) * (_nbin - 1)).astype(np.uint8)
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


def _interp_hist(qmin: float, edges: np.ndarray, cum_value: np.ndarray):
    # len(edges) == len(cum_value)
    i = np.argmax(qmin <= cum_value)
    if i == len(edges) - 1:
        return edges[-1]
    return edges[i] + (edges[i + 1] - edges[i]) * (qmin - cum_value[i])
