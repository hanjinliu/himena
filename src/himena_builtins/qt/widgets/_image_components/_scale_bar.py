from __future__ import annotations

import math
from typing import TYPE_CHECKING
from qtpy import QtWidgets as QtW, QtGui, QtCore
from himena._enum import StrEnum

if TYPE_CHECKING:
    from ._graphics_view import QImageGraphicsView


class QScaleBarItem(QtW.QGraphicsItem):
    """A scale bar item for a QGraphicsView."""

    def __init__(self, view: QImageGraphicsView):
        super().__init__()
        self._view = view
        self._scale = 1.0
        self._unit = "px"
        self._point_size = 10
        self._font = QtGui.QFont("Arial")
        self._color = QtGui.QColor(255, 255, 255)
        self._anchor_offset_px = QtCore.QPointF(8, 8)
        self._bar_size_px = QtCore.QPointF(20, 3)
        self._bar_rect = QtCore.QRectF(0, 0, 0, 0)
        self._bounding_rect = QtCore.QRectF(0, 0, 0, 0)
        self._text_visible = True
        self._auto_adjust_size = True  # TODO: implement this
        self._current_adjust_factor = 1.0
        self._anchor = ScaleBarAnchor.BOTTOM_RIGHT
        self._scale_bar_type = ScaleBarType.SHADOWED

    def update_rect(self, qrect: QtCore.QRectF):
        vw, vh = self._view.width(), self._view.height()
        scale = self._view.transform().m11()
        self._font.setPointSizeF(self._point_size)
        text_height = self._point_size / scale * 1.5 if self._text_visible else 0.0
        box_height = self._bar_size_px.y() / scale
        off = self._anchor_offset_px / scale

        if self._auto_adjust_size:
            _adjust_factor = _find_nice_factor(scale, self._scale)
            box_width = _adjust_factor / self._scale
            self._current_adjust_factor = _adjust_factor
        else:
            box_width = self._bar_size_px.x()  # do not divide by `scale`

        if self._anchor is ScaleBarAnchor.TOP_LEFT:
            box_top_left = self._view.mapToScene(0, 0) + off
        elif self._anchor is ScaleBarAnchor.TOP_RIGHT:
            box_top_left = (
                self._view.mapToScene(vw, 0)
                - QtCore.QPointF(box_width, 0)
                + QtCore.QPointF(-off.x(), off.y())
            )
        elif self._anchor is ScaleBarAnchor.BOTTOM_LEFT:
            box_top_left = (
                self._view.mapToScene(0, vh)
                - QtCore.QPointF(0, box_height + text_height)
                + QtCore.QPointF(off.x(), -off.y())
            )
        else:
            box_top_left = (
                self._view.mapToScene(vw, vh)
                - QtCore.QPointF(box_width, box_height + text_height)
                - off
            )

        self._bar_rect = QtCore.QRectF(
            box_top_left.x(), box_top_left.y(), box_width, box_height
        )
        self.update()

    def scale_bar_text(self) -> str:
        """Text to display on the scale bar."""
        if self._auto_adjust_size:
            val = self._current_adjust_factor
            return f"{val} {self._unit}"
        return f"{int(round(self._bar_size_px.x() * self._scale))} {self._unit}"

    def bar_and_text_rect(self) -> tuple[QtCore.QRectF, QtCore.QRectF]:
        scale = self._view.transform().m11()
        text = self.scale_bar_text()
        metrics = QtGui.QFontMetricsF(self._font)
        width = (metrics.width(text) + 4) / scale
        height = metrics.height() / scale
        text_rect = QtCore.QRectF(
            self._bar_rect.center().x() - width / 2,
            self._bar_rect.bottom() + 1 / scale,
            width,
            height,
        )
        bar_rect = QtCore.QRectF(self._bar_rect)
        if width > bar_rect.width():
            dw = (width - bar_rect.width()) / 2
            bar_rect.adjust(-dw, 0, dw, 0)
        return bar_rect, text_rect

    def paint(self, painter, option, widget=None):
        painter.setFont(self._font)
        text = self.scale_bar_text()
        if self._scale_bar_type is ScaleBarType.SHADOWED:
            self.draw_shadowed_scale_bar(painter, text)
        elif self._scale_bar_type is ScaleBarType.BACKGROUND:
            self.draw_backgrounded_scale_bar(painter, text)
        else:
            self.draw_simple_scale_bar(painter, text)

    def update_scale_bar(
        self,
        scale: float | None = None,
        unit: str | None = None,
        color: QtGui.QColor | None = None,
        anchor: ScaleBarAnchor | None = None,
        type: ScaleBarType | None = None,
        visible: bool | None = None,
        text_visible: bool | None = None,
    ):
        if scale is not None:
            if scale <= 0:
                raise ValueError("Scale must be positive")
            self._scale = scale
        if unit is not None:
            self._unit = unit
        if anchor is not None:
            self._anchor = ScaleBarAnchor(anchor)
        if type is not None:
            self._scale_bar_type = ScaleBarType(type)
        if color is not None:
            self._color = QtGui.QColor(color)
        if visible is not None:
            self.setVisible(visible)
        if text_visible is not None:
            self._text_visible = text_visible
        self.update_rect(self._view.sceneRect())

    def boundingRect(self):
        return self._bounding_rect

    def set_bounding_rect(self, rect: QtCore.QRectF):
        self._bounding_rect = QtCore.QRectF(rect)
        self.update()

    def draw_simple_scale_bar(self, painter: QtGui.QPainter, text: str):
        painter.setPen(QtGui.QPen(self._color, 0))
        bar_rect, text_rect = self.bar_and_text_rect()
        painter.setBrush(self._color)
        painter.drawRect(bar_rect)
        if self._text_visible:
            self._draw_text_original_scale(painter, text_rect, text)

    def draw_shadowed_scale_bar(self, painter: QtGui.QPainter, text: str):
        bar_rect, text_rect = self.bar_and_text_rect()
        shadow_rect = bar_rect.translated(0, bar_rect.height())
        color_shadow = (
            QtGui.QColor(0, 0, 0)
            if self._color.lightness() > 128
            else QtGui.QColor(255, 255, 255)
        )
        painter.setPen(QtGui.QPen(color_shadow, 0))
        painter.setBrush(color_shadow)
        painter.drawRect(shadow_rect)
        _2 = 2 / self._view.transform().m11()
        if self._text_visible:
            self._draw_text_original_scale(painter, text_rect.translated(0, _2), text)
        self.draw_simple_scale_bar(painter, text)
        painter.setPen(QtGui.QPen(self._color, 0))
        painter.setBrush(self._color)
        painter.drawRect(bar_rect)
        if self._text_visible:
            self._draw_text_original_scale(painter, text_rect, text)

    def draw_backgrounded_scale_bar(self, painter: QtGui.QPainter, text: str):
        bar_rect, text_rect = self.bar_and_text_rect()
        color_bg = (
            QtGui.QColor(0, 0, 0)
            if self._color.lightness() > 128
            else QtGui.QColor(255, 255, 255)
        )
        painter.setPen(QtGui.QPen(color_bg, 0))
        painter.setBrush(color_bg)
        _4 = 1 / self._view.transform().m11() * 4
        rect_bg = bar_rect.united(text_rect).adjusted(-_4, -_4, _4, _4)
        painter.drawRect(rect_bg)
        painter.setPen(QtGui.QPen(self._color, 0))
        painter.setBrush(self._color)
        if self._text_visible:
            self._draw_text_original_scale(painter, text_rect, text)
        self.draw_simple_scale_bar(painter, text)

    def _draw_text_original_scale(
        self,
        painter: QtGui.QPainter,
        rect: QtCore.QRectF,
        text: str,
    ):
        tr = painter.transform()
        painter.resetTransform()
        top_left = self._view.mapFromScene(rect.topLeft())
        bottom_right = self._view.mapFromScene(rect.bottomRight())
        rect = QtCore.QRectF(QtCore.QPointF(top_left), QtCore.QPointF(bottom_right))
        painter.drawText(rect, text)
        painter.setTransform(tr)


class ScaleBarType(StrEnum):
    SIMPLE = "simple"
    SHADOWED = "shadowed"
    BACKGROUND = "background"


class ScaleBarAnchor(StrEnum):
    TOP_LEFT = "top_left"
    TOP_RIGHT = "top_right"
    BOTTOM_LEFT = "bottom_left"
    BOTTOM_RIGHT = "bottom_right"


def _find_nice_factor(zoom_factor: float, image_scale: float) -> float:
    """Find a nice width for the scale bar."""
    # physical_width should be 1, 2, 5 x 10^N
    _n_pixel_for_1_unit = 1 / image_scale
    _min_logical_size = 40
    _max_logical_size = 100
    _screen_size = _n_pixel_for_1_unit * zoom_factor
    # find the smallest 1, 2, 5 x 10^N that is larger than _logical_size
    _n = -math.floor(math.log10(_screen_size)) + 1
    # now, _logical_size * 10^_n is in the range [10, 100)
    _multiplied = _screen_size * 10**_n
    _factor_int = 1
    if _multiplied < _min_logical_size / 2:
        _factor_int = 5
    elif _multiplied < _min_logical_size:
        _factor_int = 2
    elif _multiplied >= _max_logical_size * 2:
        _factor_int = 2
        _n -= 1
    elif _multiplied >= _max_logical_size:
        _factor_int = 5
        _n -= 1
    else:
        _factor_int = 1
    return _factor_int * 10**_n
