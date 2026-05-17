from __future__ import annotations
from functools import cache
from xml.etree import ElementTree

from qtpy import QtWidgets as QtW, QtCore, QtGui

from himena.consts import DefaultFontFamily, StandardType
from himena.plugins._checker import validate_protocol
from himena.standards.model_meta import TextMeta
from himena.types import WidgetDataModel
from himena.qt.magicgui import ToggleButtons
from himena_builtins.qt.widgets._shared import spacer_widget
from himena_builtins.qt.widgets._text_base import QMainTextEdit


class QSvgCanvas(QtW.QWidget):
    def __init__(self):
        from qtpy import QtSvg

        super().__init__()
        self._svg_renderer = QtSvg.QSvgRenderer()
        self._svg_renderer.setAspectRatioMode(QtCore.Qt.AspectRatioMode.KeepAspectRatio)
        self._svg_content = ""
        self._is_valid = True

    def set_text(self, content: str):
        if _is_valid := self._svg_renderer.load(content.encode()):
            self._svg_content = content
        else:
            self._svg_renderer.load(self._svg_content.encode())
        self._svg_renderer.setAspectRatioMode(QtCore.Qt.AspectRatioMode.KeepAspectRatio)
        self._is_valid = _is_valid
        self.update()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)

        painter.setBrush(ichimatsu_brush())
        painter.drawRect(self.rect())

        self._svg_renderer.render(painter)
        if not self._is_valid:
            painter.setPen(QtGui.QPen(QtCore.Qt.GlobalColor.red, 1))
            painter.setFont(QtGui.QFont(DefaultFontFamily, 12))
            painter.drawText(
                self.rect().bottomLeft() + QtCore.QPoint(2, -2), "Invalid SVG"
            )
        painter.end()


class QSvgView(QtW.QStackedWidget):
    """The viewer for a text editor with SVG content."""

    __himena_widget_id__ = "builtins:QSvgView"
    __himena_display_name__ = "Built-in SVG Viewer"

    def __init__(self):
        super().__init__()
        self._svg_canvas = QSvgCanvas()
        self._main_text_edit = QMainTextEdit(self)
        self._model_type = StandardType.SVG
        self.addWidget(self._main_text_edit)
        self.addWidget(self._svg_canvas)
        self.setCurrentIndex(1)
        self._control = QSvgViewControl(self)
        self._main_text_edit.syntax_highlight("xml")
        self._extension_default = ".svg"

    @validate_protocol
    def update_model(self, model: WidgetDataModel):
        content = str(model.value)
        self._svg_canvas.set_text(content)
        self._main_text_edit.setPlainText(content)
        self._model_type = model.type

        if isinstance(model.metadata, TextMeta):
            if sel := model.metadata.selection:
                cursor = self._main_text_edit.textCursor()
                cursor.setPosition(sel[0])
                cursor.setPosition(sel[1], QtGui.QTextCursor.MoveMode.KeepAnchor)
                self._main_text_edit.setTextCursor(cursor)
        self._model_type = model.type
        if (ext := model.extension_default) is not None:
            self._extension_default = ext

        self._model_type = model.type

    @validate_protocol
    def to_model(self) -> WidgetDataModel:
        return WidgetDataModel(
            value=self._main_text_edit.toPlainText(),
            type=self.model_type(),
            extension_default=self._extension_default,
        )

    @validate_protocol
    def model_type(self) -> StandardType:
        return self._model_type

    @validate_protocol
    def size_hint(self) -> tuple[int, int]:
        if content := self._svg_canvas._svg_content:
            et = ElementTree.fromstring(content)
            width = _size_string_to_int(et.get("width"))
            height = _size_string_to_int(et.get("height"))
            viewbox = et.get("viewBox")
            if width and height:
                return _zoom_if_needed(width, height)
            elif viewbox:
                _, _, width, height = viewbox.split()
                return _zoom_if_needed(int(width), int(height))
        return 280, 280

    @validate_protocol
    def control_widget(self) -> QMarkdownEditControl:
        return self._control

    @validate_protocol
    def is_modified(self) -> bool:
        return self._main_text_edit.is_modified()

    @validate_protocol
    def set_modified(self, value: bool) -> None:
        self._main_text_edit.document().setModified(value)

    @validate_protocol
    def is_editable(self) -> bool:
        return not self._main_text_edit.isReadOnly()

    @validate_protocol
    def set_editable(self, value: bool) -> None:
        self._main_text_edit.setReadOnly(not value)


@cache
def ichimatsu_brush() -> QtGui.QBrush:
    """Make a brush with an ichimatsu (checkered) pattern."""
    brush = QtGui.QBrush()

    pixmap = QtGui.QPixmap(60, 60)
    pixmap.fill(QtGui.QColor(255, 255, 255, 0))
    painter = QtGui.QPainter(pixmap)
    painter.fillRect(0, 0, 30, 30, QtGui.QColor(128, 128, 128, 128))
    painter.fillRect(30, 30, 30, 30, QtGui.QColor(128, 128, 128, 128))
    painter.end()

    brush.setTexture(pixmap)
    return brush


def _size_string_to_int(size_str: str) -> int | None:
    """Convert a size string like '100px' or '10cm' to an integer in pixels."""
    if _is_float(size_str):
        return int(float(size_str))
    elif size_str.endswith("px"):
        return int(float(size_str[:-2]))
    elif size_str.endswith("cm"):
        return int(float(size_str[:-2]) * 96 / 2.54)  # 96 DPI
    elif size_str.endswith("mm"):
        return int(float(size_str[:-2]) * 96 / 25.4)  # 96 DPI
    elif size_str.endswith("in"):
        return int(float(size_str[:-2]) * 96)  # 96 DPI
    else:
        return None


def _is_float(s: str) -> bool:
    """Check if the string can be converted to a float."""
    try:
        float(s)
        return True
    except ValueError:
        return False


def _zoom_if_needed(width: int, height: int) -> tuple[int, int]:
    """Zoom the SVG view by a factor if it's too small."""
    if width < 280 or height < 280:
        factor = max(280 / width, 280 / height)
        width, height = int(width * factor), int(height * factor)
    if width > 720 or height > 720:
        factor = min(720 / width, 720 / height)
        width, height = int(width * factor), int(height * factor)
    return width, height


class QMarkdownEdit(QtW.QStackedWidget):
    """The editor for markdown contents."""

    __himena_widget_id__ = "builtins:QMarkdownView"
    __himena_display_name__ = "Built-in Markdown Editor"

    def __init__(self):
        super().__init__()
        self._md_text_edit = QtW.QTextBrowser(self)
        self._md_text_edit.setOpenExternalLinks(True)
        self._md_text_edit.setOpenLinks(True)
        self._main_text_edit = QMainTextEdit(self)
        self._main_text_edit.syntax_highlight("markdown")
        self.addWidget(self._main_text_edit)
        self.addWidget(self._md_text_edit)
        self.setCurrentIndex(1)
        self._md_text_edit.setReadOnly(True)
        self._model_type = StandardType.MARKDOWN
        self._md_text_edit.setFont(QtGui.QFont(DefaultFontFamily, 10))
        self._extension_default = ".md"

        self._control = QMarkdownEditControl(self)

    @validate_protocol
    def update_model(self, model: WidgetDataModel):
        if not isinstance(value := model.value, str):
            value = str(value)
        self._main_text_edit.setPlainText(value)
        if isinstance(model.metadata, TextMeta):
            if sel := model.metadata.selection:
                cursor = self._main_text_edit.textCursor()
                cursor.setPosition(sel[0])
                cursor.setPosition(sel[1], QtGui.QTextCursor.MoveMode.KeepAnchor)
                self._main_text_edit.setTextCursor(cursor)
        self._model_type = model.type
        if (ext := model.extension_default) is not None:
            self._extension_default = ext

        self._model_type = model.type
        self._md_text_edit.setMarkdown(value)

    @validate_protocol
    def to_model(self) -> WidgetDataModel:
        return WidgetDataModel(
            value=self._main_text_edit.toPlainText(),
            type=self.model_type(),
            extension_default=self._extension_default,
        )

    @validate_protocol
    def model_type(self) -> StandardType:
        return self._model_type

    @validate_protocol
    def size_hint(self) -> tuple[int, int]:
        return (400, 400)

    @validate_protocol
    def control_widget(self) -> QMarkdownEditControl:
        return self._control

    @validate_protocol
    def is_modified(self) -> bool:
        return self._main_text_edit.is_modified()

    @validate_protocol
    def set_modified(self, value: bool) -> None:
        self._main_text_edit.document().setModified(value)

    @validate_protocol
    def is_editable(self) -> bool:
        return not self._main_text_edit.isReadOnly()

    @validate_protocol
    def set_editable(self, value: bool) -> None:
        self._main_text_edit.setReadOnly(not value)


class QMarkdownEditControl(QtW.QWidget):
    def __init__(self, parent: QMarkdownEdit):
        super().__init__()
        self._view_mode_tbtn = ToggleButtons(
            choices=["Raw", "Markdown"], value="Markdown"
        )

        layout = QtW.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(spacer_widget())
        layout.addWidget(self._view_mode_tbtn.native)

        @self._view_mode_tbtn.changed.connect
        def _(val: str):
            if val == "Raw":
                parent.setCurrentIndex(0)
            else:
                parent.setCurrentIndex(1)
                parent._md_text_edit.setMarkdown(parent._main_text_edit.toPlainText())


class QSvgViewControl(QtW.QWidget):
    def __init__(self, parent: QSvgView):
        super().__init__()
        self._view_mode_tbtn = ToggleButtons(
            choices=["Raw", "Preview"], value="Preview"
        )

        layout = QtW.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(spacer_widget())
        layout.addWidget(self._view_mode_tbtn.native)

        @self._view_mode_tbtn.changed.connect
        def _(val: str):
            if val == "Raw":
                parent.setCurrentIndex(0)
            else:
                parent.setCurrentIndex(1)
                parent._svg_canvas.set_text(parent._main_text_edit.toPlainText())
