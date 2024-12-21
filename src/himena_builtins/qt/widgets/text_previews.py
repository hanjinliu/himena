from __future__ import annotations

from qtpy import QtWidgets as QtW, QtCore, QtGui

from himena.consts import StandardType
from himena.plugins._checker import validate_protocol
from himena.types import WidgetDataModel


class QSvgPreview(QtW.QWidget):
    """The previewer for a text editor with SVG content."""

    __himena_widget_id__ = "builtins:QSvgPreview"
    __himena_display_name__ = "Built-in SVG Preview"

    def __init__(self):
        from qtpy import QtSvg

        super().__init__()
        self._svg_renderer = QtSvg.QSvgRenderer()
        self._svg_renderer.setAspectRatioMode(QtCore.Qt.AspectRatioMode.KeepAspectRatio)
        self._svg_content: str = ""
        self._is_valid = True
        self._model_type = StandardType.SVG
        self._brush = QtGui.QBrush(
            QtGui.QColor(128, 128, 128, 128), QtCore.Qt.BrushStyle.Dense4Pattern
        )
        self._brush.setTransform(QtGui.QTransform().scale(10, 10))

    @validate_protocol
    def update_model(self, model: WidgetDataModel):
        content = str(model.value)
        if _is_valid := self._svg_renderer.load(content.encode()):
            self._svg_content = content
        else:
            self._svg_renderer.load(self._svg_content.encode())
        self._is_valid = _is_valid
        self._model_type = model.type
        self.update()

    @validate_protocol
    def to_model(self) -> WidgetDataModel:
        return WidgetDataModel(
            value=self._svg_content,
            type=self.model_type(),
        )

    @validate_protocol
    def model_type(self) -> StandardType:
        return self._model_type

    @validate_protocol
    def size_hint(self) -> tuple[int, int]:
        return 280, 280

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setBrush(self._brush)
        painter.drawRect(self.rect())
        self._svg_renderer.render(painter)
        if not self._is_valid:
            painter.setPen(QtGui.QPen(QtCore.Qt.GlobalColor.red, 1))
            painter.setFont(QtGui.QFont("Arial", 12))
            painter.drawText(
                self.rect().bottomLeft() + QtCore.QPoint(2, -2), "Invalid SVG"
            )
        painter.end()


class QMarkdowPreview(QtW.QWidget):
    """The previewer for a text editor with markdown content."""

    __himena_widget_id__ = "builtins:QMarkdowPreview"
    __himena_display_name__ = "Built-in Markdown Preview"

    def __init__(self):
        super().__init__()
        self._text_edit = QtW.QTextBrowser(self)
        self._text_edit.setOpenExternalLinks(True)
        self._text_edit.setOpenLinks(True)
        layout = QtW.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._text_edit)
        self._text_edit.setReadOnly(True)
        self._model_type = StandardType.MARKDOWN
        self._text_edit.setFont(QtGui.QFont("Arial", 10))

    @validate_protocol
    def update_model(self, model: WidgetDataModel):
        self._model_type = model.type
        self._text_edit.setMarkdown(model.value)

    @validate_protocol
    def to_model(self) -> WidgetDataModel:
        return WidgetDataModel(
            value=self._text_edit.toPlainText(),
            type=self.model_type(),
        )

    @validate_protocol
    def model_type(self) -> StandardType:
        return self._model_type

    @validate_protocol
    def size_hint(self) -> tuple[int, int]:
        return (320, 400)
