from __future__ import annotations
from contextlib import contextmanager
from typing import Iterator, TYPE_CHECKING

from qtpy import QtWidgets as QtW
from qtpy import QtGui, QtCore
from superqt import QSearchableComboBox

from himena.consts import StandardType, MonospaceFontFamily
from himena.types import WidgetDataModel
from himena.model_meta import TextMeta
from himena.plugins import protocol_override

from himena._utils import OrderedSet, lru_cache
from himena.qt._qcoloredit import QColorSwatch
from himena.builtins.qt.widgets._text_base import QMainTextEdit

if TYPE_CHECKING:
    from himena.style import Theme

_POPULAR_LANGUAGES = [
    "Plain Text", "Python", "C++", "C", "Java", "JavaScript", "HTML", "CSS", "SQL",
    "Rust", "Go", "TypeScript", "Shell", "Ruby", "PHP", "Swift", "Kotlin", "Dart", "R",
    "Scala", "Perl", "Lua", "Haskell", "Julia", "MATLAB", "Markdown", "YAML", "JSON",
    "XML", "TOML", "PowerShell", "Batch", "C#", "Objective-C",
]  # fmt: skip


@lru_cache(maxsize=1)
def get_languages() -> OrderedSet[str]:
    """Get all languages supported by pygments."""
    from pygments.lexers import get_all_lexers

    langs: OrderedSet[str] = OrderedSet()
    for lang in _POPULAR_LANGUAGES:
        langs.add(lang)
    for lang, aliases, extensions, _ in get_all_lexers(plugins=False):
        langs.add(lang)
    return langs


def find_language_from_path(path: str) -> str | None:
    """Detect language from file path."""
    from pygments.lexers import get_lexer_for_filename
    from pygments.util import ClassNotFound

    try:
        lexer = get_lexer_for_filename(path)
        return lexer.name
    except ClassNotFound:
        return None


def _labeled(text: str, widget: QtW.QWidget) -> QtW.QWidget:
    new = QtW.QWidget()
    layout = QtW.QHBoxLayout(new)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.addWidget(QtW.QLabel(text))
    layout.addWidget(widget)
    return new


class QTextControl(QtW.QWidget):
    languageChanged = QtCore.Signal(str)
    tabChanged = QtCore.Signal(int)

    def __init__(self, text_edit: QMainTextEdit):
        super().__init__()
        self._text_edit = text_edit

        self._language_combobox = QSearchableComboBox()
        self._language_combobox.addItems(get_languages())
        self._language_combobox.setToolTip("Language of the document")
        self._language_combobox.setMaximumWidth(120)
        self._language_combobox.currentIndexChanged.connect(self._emit_language_changed)

        self._tab_spaces_combobox = QtW.QComboBox()
        self._tab_spaces_combobox.addItems(["1", "2", "3", "4", "5", "6", "7", "8"])
        self._tab_spaces_combobox.setCurrentText("4")
        self._tab_spaces_combobox.setToolTip("Tab size")
        self._tab_spaces_combobox.currentTextChanged.connect(
            lambda x: self.tabChanged.emit(int(x))
        )

        self._line_num = QtW.QLabel()
        self._line_num.setFixedWidth(50)

        self._encoding = QtW.QLabel("utf-8")

        layout = QtW.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        layout.addWidget(QtW.QWidget())  # spacer
        layout.addWidget(_labeled("Ln:", self._line_num))
        layout.addWidget(self._encoding)
        layout.addWidget(_labeled("Spaces:", self._tab_spaces_combobox))
        layout.addWidget(_labeled("Language:", self._language_combobox))

        # make font smaller
        font = QtGui.QFont()
        font.setFamily(MonospaceFontFamily)
        font.setPointSize(8)
        for child in self.findChildren(QtW.QWidget):
            child.setFont(font)

    def _emit_language_changed(self):
        self.languageChanged.emit(self._language_combobox.currentText())

    def _move_cursor_to_line(self, line: int):
        cursor = self._text_edit.textCursor()
        cursor.setPosition(0)
        cursor.movePosition(
            QtGui.QTextCursor.MoveOperation.NextBlock,
            QtGui.QTextCursor.MoveMode.KeepAnchor,
            line - 1,
        )
        self._text_edit.setTextCursor(cursor)


class QDefaultTextEdit(QtW.QWidget):
    def __init__(self):
        super().__init__()
        self._main_text_edit = QMainTextEdit(self)
        self._control = QTextControl(self._main_text_edit)

        self._control.languageChanged.connect(self._main_text_edit.syntax_highlight)
        self._control.tabChanged.connect(self._main_text_edit.set_tab_size)
        self._main_text_edit.cursorPositionChanged.connect(self._update_line_numbers)
        layout = QtW.QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._main_text_edit)

    @protocol_override
    @classmethod
    def display_name(cls) -> str:
        return "Built-in Text Editor"

    @protocol_override
    def control_widget(self) -> QTextControl:
        return self._control

    def setFocus(self):
        self._main_text_edit.setFocus()

    def _update_line_numbers(self):
        line_num = self._main_text_edit.textCursor().blockNumber() + 1
        self._control._line_num.setText(str(line_num))

    @protocol_override
    def update_model(self, model: WidgetDataModel):
        if not isinstance(value := model.value, str):
            value = str(value)
        self._main_text_edit.setPlainText(value)
        lang = None
        spaces = 4
        encoding = None
        if isinstance(model.metadata, TextMeta):
            lang = model.metadata.language
            spaces = model.metadata.spaces
            encoding = model.metadata.encoding
            if sel := model.metadata.selection:
                cursor = self._main_text_edit.textCursor()
                cursor.setPosition(sel[0])
                cursor.setPosition(sel[1], QtGui.QTextCursor.MoveMode.KeepAnchor)
                self._main_text_edit.setTextCursor(cursor)
        if lang is None:
            if src := model.source:
                # set default language
                lang = find_language_from_path(src.name)
        # if language could be inferred, set it
        if lang:
            self._control._language_combobox.setCurrentText(lang)
            self._control._emit_language_changed()
        self._control._tab_spaces_combobox.setCurrentText(str(spaces))
        if encoding:
            self._control._encoding.setText(encoding)
        return None

    @protocol_override
    def to_model(self) -> WidgetDataModel[str]:
        cursor = self._main_text_edit.textCursor()
        font = self._main_text_edit.font()
        return WidgetDataModel(
            value=self._main_text_edit.toPlainText(),
            type=self.model_type(),
            extension_default=".txt",
            metadata=TextMeta(
                language=self._control._language_combobox.currentText(),
                spaces=int(self._control._tab_spaces_combobox.currentText()),
                selection=(cursor.selectionStart(), cursor.selectionEnd()),
                font_family=font.family(),
                font_size=font.pointSizeF(),
            ),
        )

    @protocol_override
    def model_type(self):
        return StandardType.TEXT

    @protocol_override
    def size_hint(self) -> tuple[int, int]:
        return 400, 300

    @protocol_override
    def is_modified(self) -> bool:
        return self._main_text_edit.is_modified()

    @protocol_override
    def set_modified(self, value: bool) -> None:
        self._main_text_edit.document().setModified(value)

    @protocol_override
    def is_editable(self) -> bool:
        return not self._main_text_edit.isReadOnly()

    @protocol_override
    def set_editable(self, value: bool) -> None:
        self._main_text_edit.setReadOnly(not value)

    @protocol_override
    def theme_changed_callback(self, theme: Theme):
        text_edit = self._main_text_edit
        if theme.is_light_background():
            text_edit._code_theme = "default"
            text_edit.syntax_highlight(text_edit._language)
        else:
            text_edit._code_theme = "native"
            text_edit.syntax_highlight(text_edit._language)

    def keyPressEvent(self, a0: QtGui.QKeyEvent | None) -> None:
        if (
            a0.key() == QtCore.Qt.Key.Key_F
            and a0.modifiers() & QtCore.Qt.KeyboardModifier.ControlModifier
        ):
            self._main_text_edit._find_string()
            return None
        return super().keyPressEvent(a0)


class QDefaultRichTextEdit(QtW.QWidget):
    def __init__(self):
        super().__init__()
        self._main_text_edit = QtW.QTextEdit(self)
        layout = QtW.QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._main_text_edit)
        self._control = QRichTextEditControl(self)

    def initPlainText(self, text: str):
        self._main_text_edit.setHtml(text)

    def toPlainText(self) -> str:
        return self._main_text_edit.toPlainText()

    def setFocus(self):
        self._main_text_edit.setFocus()

    @protocol_override
    @classmethod
    def display_name(cls) -> str:
        return "Built-in HTML Text Editor"

    @protocol_override
    def update_model(self, model: WidgetDataModel[str]):
        self.initPlainText(model.value)
        return None

    @protocol_override
    def to_model(self) -> WidgetDataModel[str]:
        cursor = self._main_text_edit.textCursor()
        font = self._main_text_edit.font()
        return WidgetDataModel(
            value=self._main_text_edit.toHtml(),
            type=self.model_type(),
            extension_default=".html",
            metadata=TextMeta(
                language="HTML",
                selection=(cursor.selectionStart(), cursor.selectionEnd()),
                font_family=font.family(),
                font_size=font.pointSizeF(),
            ),
        )

    @protocol_override
    def model_type(self):
        return StandardType.HTML

    @protocol_override
    def size_hint(self) -> tuple[int, int]:
        return 400, 300

    @protocol_override
    def is_modified(self) -> bool:
        return False

    @protocol_override
    def set_modified(self, value: bool) -> None:
        self._main_text_edit.document().setModified(value)

    @protocol_override
    def is_editable(self) -> bool:
        return False

    @protocol_override
    def set_editable(self, value: bool) -> None:
        self._main_text_edit.setReadOnly(not value)

    @protocol_override
    def control_widget(self) -> QRichTextEditControl:
        return self._control


def _make_btn(text: str, tooltip: str, callback) -> QtW.QPushButton:
    btn = QtW.QPushButton(text)
    btn.setFixedWidth(20)
    btn.setToolTip(tooltip)
    btn.clicked.connect(callback)
    return btn


def _make_color_swatch(label: str, tooltip: str, callback) -> QtW.QWidget:
    group = QtW.QWidget()
    layout = QtW.QHBoxLayout(group)
    layout.setContentsMargins(0, 0, 0, 0)
    swatch = QColorSwatch()
    swatch.setQColor(QtGui.QColor(0, 0, 0, 0))
    swatch.setToolTip(tooltip)
    swatch.setFixedSize(25, 20)
    swatch.colorChanged.connect(callback)
    label_widget = QtW.QLabel(label)
    label_widget.setAlignment(
        QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter
    )
    label_widget.setFixedWidth(20)
    layout.addWidget(label_widget)
    layout.addWidget(swatch)
    return group


class QRichTextEditControl(QtW.QWidget):
    def __init__(self, text_edit: QDefaultRichTextEdit):
        super().__init__()
        self._foreground_color_edit = _make_color_swatch(
            label="FG:",
            tooltip="Change Foreground Color",
            callback=self._on_foreground_color_changed,
        )
        self._background_color_edit = _make_color_swatch(
            label="BG:",
            tooltip="Change Background Color",
            callback=self._on_background_color_changed,
        )
        self._toggle_bold_button = _make_btn(
            "B",
            tooltip="Toggle Bold",
            callback=self._on_toggle_bold,
        )
        self._toggle_it_button = _make_btn(
            "I",
            tooltip="Toggle Italic",
            callback=self._on_toggle_italic,
        )
        self._toggle_underline_button = _make_btn(
            "U",
            tooltip="Toggle Underline",
            callback=self._on_toggle_underline,
        )
        self._toggle_strike_button = _make_btn(
            "S", tooltip="Toggle Strike", callback=self._on_toggle_strike
        )
        spacer = QtW.QWidget()
        spacer.setSizePolicy(
            QtW.QSizePolicy.Policy.Expanding, QtW.QSizePolicy.Policy.Preferred
        )
        layout = QtW.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(spacer)
        layout.addWidget(self._foreground_color_edit)
        layout.addWidget(self._background_color_edit)
        layout.addWidget(self._toggle_bold_button)
        layout.addWidget(self._toggle_it_button)
        layout.addWidget(self._toggle_underline_button)
        layout.addWidget(self._toggle_strike_button)

        self._text_edit = text_edit

    def _on_foreground_color_changed(self, color: QtGui.QColor):
        with self._merging_format() as fmt:
            fmt.setForeground(color)

    def _on_background_color_changed(self, color: QtGui.QColor):
        with self._merging_format() as fmt:
            fmt.setBackground(color)

    def _on_toggle_bold(self):
        with self._merging_format() as fmt:
            fmt.setFontWeight(
                QtGui.QFont.Weight.Bold
                if not fmt.font().bold()
                else QtGui.QFont.Weight.Normal
            )

    def _on_toggle_italic(self):
        with self._merging_format() as fmt:
            fmt.setFontItalic(not fmt.font().italic())

    def _on_toggle_underline(self):
        with self._merging_format() as fmt:
            fmt.setFontUnderline(not fmt.font().underline())

    def _on_toggle_strike(self):
        with self._merging_format() as fmt:
            fmt.setFontStrikeOut(not fmt.font().strikeOut())

    @contextmanager
    def _merging_format(self) -> Iterator[QtGui.QTextCharFormat]:
        cursor = self._text_edit._main_text_edit.textCursor()
        fmt = cursor.charFormat()
        yield fmt
        cursor.mergeCharFormat(fmt)
        self._text_edit._main_text_edit.setTextCursor(cursor)
