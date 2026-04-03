from __future__ import annotations
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, TYPE_CHECKING
from encodings import aliases, normalize_encoding

from qtpy import QtWidgets as QtW
from qtpy import QtGui, QtCore

from himena.consts import StandardType
from himena.types import WidgetDataModel
from himena.standards.model_meta import TextMeta
from himena.plugins import validate_protocol, config_field
from himena.widgets import current_instance

from himena.utils.collections import OrderedSet
from himena.utils.misc import lru_cache
from himena.qt import QComboButton, QColorSwatch
from himena_builtins.qt.widgets._text_base import QMainTextEdit, POINT_SIZES, TAB_SIZES
from himena_builtins.qt.widgets._shared import labeled, spacer_widget

if TYPE_CHECKING:
    from himena.style import Theme

_POPULAR_LANGUAGES = [
    "Plain Text", "Python", "C++", "C", "Java", "JavaScript", "HTML", "CSS", "SQL",
    "Rust", "Go", "TypeScript", "Shell", "Ruby", "PHP", "Swift", "Kotlin", "Dart", "R",
    "Scala", "Perl", "Lua", "Haskell", "Julia", "MATLAB", "Markdown", "YAML", "JSON",
    "XML", "TOML", "PowerShell", "Batch", "C#", "Objective-C",
]  # fmt: skip
_POPULAR_ENCODINGS = [
    "utf-8", "utf-16", "ascii", "latin-1", "shift-jis", "gbk", "euc-kr",
]  # fmt: skip


class QTextEdit(QtW.QWidget):
    """Default text editor widget.

    This widget supports syntax highlighting for various programming languages.
    Ctrl+Click to open the URL link or local file under the cursor.
    """

    __himena_widget_id__ = "builtins:QTextEdit"
    __himena_display_name__ = "Built-in Text Editor"

    def __init__(self):
        super().__init__()
        self._main_text_edit = QMainTextEdit(self)
        self._control = QTextControl(self._main_text_edit)

        self._control.languageChanged.connect(self._on_language_changed)
        self._control.tabChanged.connect(self._on_tab_size_changed)
        self._main_text_edit.cursorPositionChanged.connect(self._update_line_numbers)
        layout = QtW.QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._main_text_edit)
        self._model_type = StandardType.TEXT
        self._extension_default = ".txt"

    @validate_protocol
    def control_widget(self) -> QTextControl:
        return self._control

    @validate_protocol
    def update_configs(self, configs: TextEditConfigs):
        self._main_text_edit._default_font.setPointSize(configs.default_font_size)
        self._main_text_edit.setFont(self._main_text_edit._default_font)
        self._control._tab_spaces_btn.setCurrentText(str(configs.default_tab_size))

    @validate_protocol
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
            if isinstance(src := model.source, Path):
                # set default language
                lang = find_language_from_path(src.name)
        # if language could be inferred, set it
        if lang:
            self._control._language_btn.setCurrentText(lang)
            self._control.languageChanged.emit(lang)
        self._control._tab_spaces_btn.setCurrentText(str(spaces))
        if encoding:
            enc = normalize_encoding(encoding).replace("_", "-")
            self._control._encoding_btn.setCurrentText(enc)
        self._model_type = model.type
        if (ext := model.extension_default) is not None:
            self._extension_default = ext

    @validate_protocol
    def to_model(self) -> WidgetDataModel[str]:
        cursor = self._main_text_edit.textCursor()
        font = self._main_text_edit.font()
        return WidgetDataModel(
            value=self._main_text_edit.toPlainText(),
            type=self.model_type(),
            extension_default=self._extension_default,
            metadata=TextMeta(
                language=self._control._language_btn.currentText(),
                spaces=int(self._control._tab_spaces_btn.currentText()),
                selection=(cursor.selectionStart(), cursor.selectionEnd()),
                encoding=self._control._encoding_btn.currentText(),
                font_family=font.family(),
                font_size=font.pointSizeF(),
            ),
        )

    @validate_protocol
    def model_type(self):
        return self._model_type

    @validate_protocol
    def size_hint(self) -> tuple[int, int]:
        return 400, 300

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

    @validate_protocol
    def widget_added_callback(self):
        self._main_text_edit.setFont(self._main_text_edit._default_font)

    @validate_protocol
    def theme_changed_callback(self, theme: Theme):
        text_edit = self._main_text_edit
        if theme.is_light_background():
            text_edit._code_theme = "default"
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

    def setFocus(self):
        self._main_text_edit.setFocus()

    def _update_line_numbers(self):
        line_num = self._main_text_edit.textCursor().blockNumber() + 1
        self._control._line_num.setText(str(line_num))

    def _on_language_changed(self, language: str):
        self._main_text_edit.syntax_highlight(language)
        if language.lower() == "python":
            self._model_type = StandardType.PYTHON
            self._extension_default = ".py"
        else:
            self._model_type = StandardType.TEXT
            self._extension_default = ".txt"
        self._control._language_btn.setCurrentText(language)

    def _on_tab_size_changed(self, tab_size: int):
        self._main_text_edit.set_tab_size(tab_size)
        self._control._tab_spaces_btn.setCurrentText(str(tab_size))


class QRichTextEdit(QtW.QWidget):
    __himena_widget_id__ = "builtins:QRichTextEdit"
    __himena_display_name__ = "Built-in HTML Text Editor"

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

    def setFocus(self):
        self._main_text_edit.setFocus()

    @validate_protocol
    def update_model(self, model: WidgetDataModel[str]):
        self.initPlainText(model.value)
        return None

    @validate_protocol
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

    @validate_protocol
    def model_type(self):
        return StandardType.HTML

    @validate_protocol
    def size_hint(self) -> tuple[int, int]:
        return 400, 300

    @validate_protocol
    def is_modified(self) -> bool:
        return False

    @validate_protocol
    def set_modified(self, value: bool) -> None:
        self._main_text_edit.document().setModified(value)

    @validate_protocol
    def is_editable(self) -> bool:
        return False

    @validate_protocol
    def set_editable(self, value: bool) -> None:
        self._main_text_edit.setReadOnly(not value)
        self._control.setEnabled(value)

    @validate_protocol
    def control_widget(self) -> QRichTextEditControl:
        return self._control


class QRichTextPushButton(QtW.QPushButton):
    def __init__(self, text: str):
        super().__init__()
        self._label = QtW.QLabel(text, self)
        layout = QtW.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._label)
        self._label.setAttribute(QtCore.Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._label.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)
        self._label.setSizePolicy(
            QtW.QSizePolicy.Policy.Expanding,
            QtW.QSizePolicy.Policy.Expanding,
        )
        self._label.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignCenter | QtCore.Qt.AlignmentFlag.AlignVCenter
        )


def _make_btn(text: str, tooltip: str, callback) -> QtW.QPushButton:
    btn = QRichTextPushButton(text)
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
    def __init__(self, text_edit: QRichTextEdit):
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
            "<b>B</b>",
            tooltip="Toggle Bold",
            callback=self._on_toggle_bold,
        )
        self._toggle_it_button = _make_btn(
            "<i>I</i>",
            tooltip="Toggle Italic",
            callback=self._on_toggle_italic,
        )
        self._toggle_underline_button = _make_btn(
            "<u>U</u>",
            tooltip="Toggle Underline",
            callback=self._on_toggle_underline,
        )
        self._toggle_strike_button = _make_btn(
            "<s>S</s>", tooltip="Toggle Strike", callback=self._on_toggle_strike
        )
        layout = QtW.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(spacer_widget())
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


@dataclass
class TextEditConfigs:
    default_font_size: int = config_field(
        default=10,
        label="Default font size (pt).",
        choices=POINT_SIZES,
    )
    default_tab_size: int = config_field(
        default=4,
        label="Default tab size.",
        choices=TAB_SIZES,
    )


@lru_cache(maxsize=1)
def get_languages() -> OrderedSet[str]:
    """Get all languages supported by pygments."""
    from pygments.lexers import get_all_lexers

    langs: OrderedSet[str] = OrderedSet()
    for lang in _POPULAR_LANGUAGES:
        langs.add(lang)
    for lang, _aliases, _extensions, _ in get_all_lexers(plugins=False):
        langs.add(lang)
    return langs


@lru_cache(maxsize=1)
def get_encodings() -> OrderedSet[str]:
    """Get popular encodings."""
    encs: OrderedSet[str] = OrderedSet()
    for enc in _POPULAR_ENCODINGS:
        encs.add(enc)
    for enc in aliases.aliases.values():
        encs.add(enc.replace("_", "-"))
    return encs


def find_language_from_path(path: str) -> str | None:
    """Detect language from file path."""
    from pygments.lexers import get_lexer_for_filename
    from pygments.util import ClassNotFound

    # pygment lexer for svg is not available
    if path.endswith(".svg"):
        return "XML"

    try:
        lexer = get_lexer_for_filename(path)
        return lexer.name
    except ClassNotFound:
        return None


class QTextControl(QtW.QWidget):
    languageChanged = QtCore.Signal(str)
    tabChanged = QtCore.Signal(int)

    def __init__(self, text_edit: QMainTextEdit):
        super().__init__()
        self._text_edit = text_edit

        self._language_btn = QComboButton("Plain Text")
        self._language_btn.setMessage("Select the language for syntax highlighting.")
        self._language_btn.setChoices(get_languages)
        self._language_btn.setFormatter("Language: {}")
        self._language_btn.setToolTip("Language of the document. Click to change.")
        self._language_btn.currentTextChanged.connect(self.languageChanged.emit)

        self._tab_spaces_btn = QComboButton("4")
        self._tab_spaces_btn.setMessage("Select the number of spaces for a tab.")
        self._tab_spaces_btn.setChoices([str(i) for i in TAB_SIZES])
        self._tab_spaces_btn.setFormatter("Spaces: {}")
        self._tab_spaces_btn.setToolTip("Tab spaces. Click to change.")
        self._tab_spaces_btn.currentTextChanged.connect(
            lambda x: self.tabChanged.emit(int(x))
        )

        self._line_num = QtW.QLabel()
        self._line_num.setFixedWidth(50)

        self._wordwrap_btn = QComboButton("Word Wrap")
        self._wordwrap_btn.setMessage("Select the word wrap mode.")
        self._wordwrap_btn.setChoices(["No Wrap", "Word Wrap", "Wrap Anywhere"])
        self._wordwrap_btn.setToolTip("Word wrap mode. Click to change.")
        self._wordwrap_btn.currentTextChanged.connect(self._wordwrap_changed)

        self._encoding_btn = QComboButton("utf-8")
        self._encoding_btn.setToolTip("Encoding of the document. Click to change.")
        self._encoding_btn.setChoices(get_encodings)

        layout = QtW.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        layout.setSpacing(1)
        layout.addWidget(spacer_widget())
        layout.addWidget(labeled("Ln:", self._line_num))
        layout.addWidget(self._encoding_btn)
        layout.addWidget(self._wordwrap_btn)
        layout.addWidget(self._tab_spaces_btn)
        layout.addWidget(self._language_btn)

        # make font smaller
        for child in self.findChildren(QtW.QWidget):
            font = child.font()
            font.setPointSize(8)
            child.setFont(font)

    def _wordwrap_changed(self, mode_str: str):
        """Enable or disable word wrap."""
        match mode_str:
            case "Word Wrap":
                mode = QtGui.QTextOption.WrapMode.WordWrap
            case "Wrap Anywhere":
                mode = QtGui.QTextOption.WrapMode.WrapAnywhere
            case _:
                mode = QtGui.QTextOption.WrapMode.NoWrap
        self._text_edit.setWordWrapMode(mode)

    def _select_encoding(self):
        current_instance().exec_action("builtins:text:change-encoding")

    # def _move_cursor_to_line(self, line: int):
    #     cursor = self._text_edit.textCursor()
    #     cursor.setPosition(0)
    #     cursor.movePosition(
    #         QtGui.QTextCursor.MoveOperation.NextBlock,
    #         QtGui.QTextCursor.MoveMode.KeepAnchor,
    #         line - 1,
    #     )
    #     self._text_edit.setTextCursor(cursor)
