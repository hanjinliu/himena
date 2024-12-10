from __future__ import annotations

from qtpy import QtWidgets as QtW, QtCore, QtGui

from himena.consts import StandardType
from himena.plugins._checker import protocol_override
from himena.types import WidgetDataModel


class QSvgPreview(QtW.QWidget):
    __himena_widget_id__ = "builtins:QSvgPreview"
    __himena_display_name__ = "Built-in SVG Preview"

    def __init__(self):
        from qtpy import QtSvg

        super().__init__()
        self._svg_renderer = QtSvg.QSvgRenderer()
        self._svg_renderer.setAspectRatioMode(QtCore.Qt.AspectRatioMode.KeepAspectRatio)
        self._svg_content: str = ""
        self._is_valid = True

    @protocol_override
    def update_model(self, model: WidgetDataModel):
        content = str(model.value)
        if _is_valid := self._svg_renderer.load(content.encode()):
            self._svg_content = content
        else:
            self._svg_renderer.load(self._svg_content.encode())
        self._is_valid = _is_valid
        self.update()

    @protocol_override
    def to_model(self) -> WidgetDataModel:
        return WidgetDataModel(
            value=self._svg_content,
            type=StandardType.SVG,
        )

    @protocol_override
    def size_hint(self) -> QtCore.QSize:
        return QtCore.QSize(280, 280)

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        self._svg_renderer.render(painter)
        if not self._is_valid:
            painter.setPen(QtGui.QPen(QtCore.Qt.GlobalColor.red, 1))
            painter.setFont(QtGui.QFont("Arial", 12))
            painter.drawText(
                self.rect().bottomLeft() + QtCore.QPoint(2, -2), "Invalid SVG"
            )
        painter.end()
