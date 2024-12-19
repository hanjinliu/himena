from __future__ import annotations

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
        self._auto_adjust_size = False  # TODO: implement this
        self._anchor = ScaleBarAnchor.BOTTOM_RIGHT
        self._scale_bar_type = ScaleBarType.SHADOWED

    def update_rect(self, qrect: QtCore.QRectF):
        vw, vh = self._view.width(), self._view.height()
        scale = self._view.transform().m11()
        self._font.setPointSizeF(self._point_size / scale)

        box_width = self._bar_size_px.x()  # do not divide by `scale`
        text_height = self._point_size / scale * 1.5 if self._text_visible else 0.0
        box_height = self._bar_size_px.y() / scale
        off = self._anchor_offset_px / scale
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

    def bar_rect(self) -> QtCore.QRectF:
        return self._bar_rect

    def scale_bar_text(self) -> str:
        return f"{int(round(self._bar_size_px.x() * self._scale))} {self._unit}"

    def text_rect(self) -> QtCore.QRectF:
        scale = self._view.transform().m11()
        text = self.scale_bar_text()
        metrics = QtGui.QFontMetricsF(self._font)
        width = metrics.width(text)
        height = metrics.height()
        return QtCore.QRectF(
            self._bar_rect.center().x() - width / 2,
            self._bar_rect.bottom() + 1 / scale,
            width,
            height,
        )

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
        bar_rect = self.bar_rect()
        painter.setBrush(self._color)
        painter.drawRect(bar_rect)
        if self._text_visible:
            painter.drawText(self.text_rect(), text)

    def draw_shadowed_scale_bar(self, painter: QtGui.QPainter, text: str):
        bar_rect = self.bar_rect()
        shadow_rect = bar_rect.translated(0, bar_rect.height())
        text_rect = self.text_rect()
        color_shadow = (
            QtGui.QColor(0, 0, 0)
            if self._color.lightness() > 128
            else QtGui.QColor(255, 255, 255)
        )
        painter.setPen(QtGui.QPen(color_shadow, 0))
        painter.setBrush(color_shadow)
        painter.drawRect(shadow_rect)
        _1 = 1 / self._view.transform().m11()
        if self._text_visible:
            painter.drawText(text_rect.translated(0, 2 * _1), text)
        self.draw_simple_scale_bar(painter, text)
        painter.setPen(QtGui.QPen(self._color, 0))
        painter.setBrush(self._color)
        painter.drawRect(bar_rect)
        if self._text_visible:
            painter.drawText(text_rect, text)

    def draw_backgrounded_scale_bar(self, painter: QtGui.QPainter, text: str):
        bar_rect = self.bar_rect()
        text_rect = self.text_rect()
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
            painter.drawText(text_rect, text)
        self.draw_simple_scale_bar(painter, text)


class ScaleBarType(StrEnum):
    SIMPLE = "simple"
    SHADOWED = "shadowed"
    BACKGROUND = "background"


class ScaleBarAnchor(StrEnum):
    TOP_LEFT = "top_left"
    TOP_RIGHT = "top_right"
    BOTTOM_LEFT = "bottom_left"
    BOTTOM_RIGHT = "bottom_right"
