from __future__ import annotations
from typing import Iterator

from qtpy import QtWidgets as QtW
from qtpy import QtGui, QtCore
from superqt import QSearchableComboBox

from royalapp.consts import StandardTypes
from royalapp.types import WidgetDataModel
from royalapp.qt._qt_consts import MonospaceFontFamily

from royalapp._utils import OrderedSet, lru_cache


_POPULAR_LANGUAGES = [
    "Plain Text", "Python", "C++", "C", "Java", "JavaScript", "HTML", "CSS", "SQL",
    "Rust", "Go", "TypeScript", "Shell", "Ruby", "PHP", "Swift", "Kotlin", "Dart", "R",
    "Scala", "Perl", "Lua", "Haskell", "Julia", "MATLAB", "Markdown", "YAML", "JSON",
    "XML", "TOML",
]  # fmt: skip


@lru_cache
def get_languages() -> OrderedSet[str]:
    from pygments.lexers import get_all_lexers

    langs: OrderedSet[str] = OrderedSet()
    for lang in _POPULAR_LANGUAGES:
        langs.add(lang)
    for lang, aliases, extensions, _ in get_all_lexers(plugins=False):
        langs.add(lang)
    return langs


@lru_cache(maxsize=20)
def find_language_from_path(path: str) -> str | None:
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


class QMainTextEdit(QtW.QPlainTextEdit):
    def __init__(self, parent: QtW.QWidget | None = None):
        super().__init__(parent)
        self.setWordWrapMode(QtGui.QTextOption.WrapMode.NoWrap)
        font = QtGui.QFont(MonospaceFontFamily)
        self.setFont(font)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._tab_size = 4
        self._highlight = None

    def is_modified(self) -> bool:
        return self.document().isModified()

    def syntax_highlight(self, lang: str | None = "python", theme: str = "default"):
        """Highlight syntax."""
        if lang is None or lang == "Plain Text":
            if self._highlight is not None:
                self._highlight.setDocument(None)
            return None
        from superqt.utils import CodeSyntaxHighlight

        highlight = CodeSyntaxHighlight(self.document(), lang, theme=theme)
        self._highlight = highlight
        return None

    def tab_size(self):
        return self._tab_size

    def set_tab_size(self, size: int):
        self._tab_size = size

    def event(self, ev: QtCore.QEvent):
        try:
            if ev.type() == QtCore.QEvent.Type.KeyPress:
                assert isinstance(ev, QtGui.QKeyEvent)
                _key = ev.key()
                _mod = ev.modifiers()
                if (
                    _key == QtCore.Qt.Key.Key_Tab
                    and _mod == QtCore.Qt.KeyboardModifier.NoModifier
                ):
                    return self._tab_event()
                elif (
                    _key == QtCore.Qt.Key.Key_Tab
                    and _mod & QtCore.Qt.KeyboardModifier.ShiftModifier
                ):
                    return self._back_tab_event()
                elif _key == QtCore.Qt.Key.Key_Backtab:
                    return self._back_tab_event()
                # move selected lines up or down
                elif (
                    _key in (QtCore.Qt.Key.Key_Up, QtCore.Qt.Key.Key_Down)
                    and _mod & QtCore.Qt.KeyboardModifier.AltModifier
                ):
                    cursor = self.textCursor()
                    cursor0 = self.textCursor()
                    start = cursor.selectionStart()
                    end = cursor.selectionEnd()
                    Op = QtGui.QTextCursor.MoveOperation
                    _keep = QtGui.QTextCursor.MoveMode.KeepAnchor
                    if _key == QtCore.Qt.Key.Key_Up and min(start, end) > 0:
                        cursor0.setPosition(start)
                        cursor0.movePosition(Op.PreviousBlock)
                        cursor0.movePosition(Op.StartOfLine)
                        cursor0.movePosition(Op.EndOfLine, _keep)
                        cursor0.movePosition(Op.NextCharacter, _keep)
                        txt = cursor0.selectedText()
                        cursor0.removeSelectedText()
                        # NOTE: cursor position changed!
                        cursor0.setPosition(cursor.selectionEnd())
                        cursor0.movePosition(Op.EndOfLine)
                        if cursor0.position() == self.document().characterCount() - 1:
                            cursor0.insertText("\n")
                            txt = txt.rstrip("\u2029")
                        if cursor.position() == self.document().characterCount() - 1:
                            cursor.movePosition(Op.Up)
                        cursor0.movePosition(Op.NextCharacter)
                        cursor0.insertText(txt)
                        self.setTextCursor(cursor)
                    elif (
                        _key == QtCore.Qt.Key.Key_Down
                        and max(start, end) < self.document().characterCount() - 1
                    ):
                        cursor0.setPosition(end)
                        cursor0.movePosition(Op.EndOfLine)
                        cursor0.movePosition(Op.NextCharacter, _keep)
                        cursor0.movePosition(Op.EndOfLine, _keep)
                        txt = cursor0.selectedText()
                        cursor0.removeSelectedText()
                        # NOTE: cursor position changed!
                        cursor0.setPosition(cursor.selectionStart())
                        cursor0.movePosition(Op.StartOfLine)
                        if cursor0.position() == 0:
                            cursor0.insertText("\n")
                            txt = txt.lstrip("\u2029")
                        cursor0.movePosition(Op.PreviousCharacter)
                        cursor0.insertText(txt)
                        self.setTextCursor(cursor)
                    return True
                elif _key in (QtCore.Qt.Key.Key_Enter, QtCore.Qt.Key.Key_Return):
                    # get current line, check if it has tabs at the beginning
                    # if yes, insert the same number of tabs at the next line
                    self._new_line_event()
                    return True
                elif (
                    _key == QtCore.Qt.Key.Key_Backspace
                    and _mod == QtCore.Qt.KeyboardModifier.NoModifier
                ):
                    # delete 4 spaces
                    _cursor = self.textCursor()
                    _cursor.movePosition(
                        QtGui.QTextCursor.MoveOperation.StartOfLine,
                        QtGui.QTextCursor.MoveMode.KeepAnchor,
                    )
                    line = _cursor.selectedText()
                    if line.endswith("    ") and not self.textCursor().hasSelection():
                        for _ in range(4):
                            self.textCursor().deletePreviousChar()
                        return True
                elif (
                    _key == QtCore.Qt.Key.Key_D
                    and _mod & QtCore.Qt.KeyboardModifier.ControlModifier
                ):
                    return self._select_word_event()
                elif (
                    _key == QtCore.Qt.Key.Key_L
                    and _mod & QtCore.Qt.KeyboardModifier.ControlModifier
                ):
                    return self._select_line_event()
                elif (
                    _key == QtCore.Qt.Key.Key_Home
                    and _mod == QtCore.Qt.KeyboardModifier.NoModifier
                ):
                    return self._home_event()
                elif (
                    _key == QtCore.Qt.Key.Key_V
                    and _mod & QtCore.Qt.KeyboardModifier.ControlModifier
                ):
                    clip = QtGui.QGuiApplication.clipboard()
                    text = clip.text().replace("\t", " " * self.tab_size())
                    cursor = self.textCursor()
                    cursor.insertText(text)
                    return True

        except Exception:
            pass
        return super().event(ev)

    def _iter_selected_lines(self) -> Iterator[QtGui.QTextCursor]:
        """Iterate text cursors for each selected line."""
        _cursor = self.textCursor()
        start, end = sorted([_cursor.selectionStart(), _cursor.selectionEnd()])
        _cursor.setPosition(start)
        _cursor.movePosition(QtGui.QTextCursor.MoveOperation.StartOfLine)
        nline = 0
        while True:
            _cursor.movePosition(QtGui.QTextCursor.MoveOperation.EndOfLine)
            _cursor.movePosition(QtGui.QTextCursor.MoveOperation.NextCharacter)
            nline += 1
            if _cursor.position() >= end:
                break

        _cursor.setPosition(start)
        for _ in range(nline):
            _cursor.movePosition(QtGui.QTextCursor.MoveOperation.EndOfLine)
            yield _cursor
            _cursor.movePosition(QtGui.QTextCursor.MoveOperation.EndOfLine)
            _cursor.movePosition(QtGui.QTextCursor.MoveOperation.NextCharacter)

    def _tab_event(self):
        if self.textCursor().hasSelection():
            for cursor in self._iter_selected_lines():
                self._add_at_the_start(" " * self.tab_size(), cursor)
        else:
            line = self._text_of_line_before_cursor()
            nspace = line.count(" ")
            if nspace % 4 == 0:
                self.textCursor().insertText(" " * self.tab_size())
            else:
                self.textCursor().insertText(" " * 4 - nspace % 4)
        return True

    def _add_at_the_start(self, text: str, cursor: QtGui.QTextCursor):
        cursor.movePosition(QtGui.QTextCursor.MoveOperation.StartOfLine)
        cursor.insertText(text)

    def _remove_at_the_start(self, text: str, cursor: QtGui.QTextCursor):
        line = cursor.block().text()
        if line.startswith(text):
            cursor.movePosition(QtGui.QTextCursor.MoveOperation.StartOfLine)
            cursor.movePosition(
                QtGui.QTextCursor.MoveOperation.Right,
                QtGui.QTextCursor.MoveMode.KeepAnchor,
                len(text),
            )
            cursor.removeSelectedText()

    def _back_tab_event(self):
        # unindent
        for cursor in self._iter_selected_lines():
            self._remove_at_the_start(" " * self.tab_size(), cursor)
        return True

    def _text_of_line_before_cursor(self):
        _cursor = self.textCursor()
        _cursor.movePosition(
            QtGui.QTextCursor.MoveOperation.StartOfLine,
            QtGui.QTextCursor.MoveMode.KeepAnchor,
        )
        return _cursor.selectedText()

    def _select_word_event(self):
        cursor = self.textCursor()
        cursor.movePosition(QtGui.QTextCursor.MoveOperation.NextWord)
        cursor.movePosition(
            QtGui.QTextCursor.MoveOperation.PreviousWord,
            QtGui.QTextCursor.MoveMode.KeepAnchor,
        )
        self.setTextCursor(cursor)
        return True

    def _select_line_event(self):
        cursor = self.textCursor()
        cursor.movePosition(QtGui.QTextCursor.MoveOperation.StartOfLine)
        cursor.movePosition(
            QtGui.QTextCursor.MoveOperation.EndOfLine,
            QtGui.QTextCursor.MoveMode.KeepAnchor,
        )
        cursor.movePosition(
            QtGui.QTextCursor.MoveOperation.NextCharacter,
            QtGui.QTextCursor.MoveMode.KeepAnchor,
        )
        self.setTextCursor(cursor)
        return True

    def _home_event(self):
        # fn + left
        cursor = self.textCursor()
        cursor.movePosition(
            QtGui.QTextCursor.MoveOperation.StartOfLine,
            QtGui.QTextCursor.MoveMode.KeepAnchor,
        )
        text = cursor.selectedText()
        if all(c == " " for c in text):
            cursor.clearSelection()
        else:
            text_lstrip = text.lstrip()
            nmove = len(text) - len(text_lstrip)
            cursor.clearSelection()
            for _ in range(nmove):
                cursor.movePosition(QtGui.QTextCursor.MoveOperation.Right)

        self.setTextCursor(cursor)
        return True

    def _new_line_event(self):
        line = self._text_of_line_before_cursor()
        cursor = self.textCursor()
        line_rstripped = line.rstrip()
        indent = _get_indents(line, self.tab_size())
        if line_rstripped == "":
            cursor.insertText("\n" + indent)
            self.setTextCursor(cursor)
            return
        cursor.insertText("\n" + indent)
        self.setTextCursor(cursor)


def _get_indents(text: str, tab_spaces: int = 4) -> str:
    chars = []
    for c in text:
        if c == " ":
            chars.append(" ")
        elif c == "\t":
            chars.append(" " * tab_spaces)
        else:
            break
    return "".join(chars)


class QTextFooter(QtW.QWidget):
    languageChanged = QtCore.Signal(str)
    tabChanged = QtCore.Signal(int)

    def __init__(self, parent: QtW.QWidget | None = None):
        super().__init__(parent)

        self._language_combobox = QSearchableComboBox()
        self._language_combobox.addItems(get_languages())
        self._language_combobox.setToolTip("Language of the document")
        self._language_combobox.currentIndexChanged.connect(self._emit_language_changed)

        self._tab_spaces_combobox = QtW.QComboBox()
        self._tab_spaces_combobox.addItems(["1", "2", "3", "4", "5", "6", "7", "8"])
        self._tab_spaces_combobox.setCurrentText("4")
        self._tab_spaces_combobox.setToolTip("Tab size")
        self._tab_spaces_combobox.currentTextChanged.connect(
            lambda x: self.tabChanged(int(x))
        )

        layout = QtW.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
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


class QDefaultTextEdit(QtW.QWidget):
    def __init__(self):
        super().__init__()
        self._main_text_edit = QMainTextEdit(self)
        self._footer = QTextFooter(self)

        self._footer.languageChanged.connect(self._main_text_edit.syntax_highlight)
        self._footer.tabChanged.connect(self._main_text_edit.set_tab_size)
        layout = QtW.QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._main_text_edit)
        layout.addWidget(self._footer)

    def initPlainText(self, text: str):
        self._main_text_edit.setPlainText(text)

    def toPlainText(self) -> str:
        return self._main_text_edit.toPlainText()

    @classmethod
    def from_model(cls, model: WidgetDataModel) -> QDefaultTextEdit:
        self = cls()
        self.initPlainText(model.value)
        if model.source is not None:
            self.setObjectName(model.source.name)
            # set default language
            if lang := find_language_from_path(model.source.name):
                self._footer._language_combobox.setCurrentText(lang)
                self._footer._emit_language_changed()
        else:
            self._main_text_edit.document().setModified(True)
        return self

    def to_model(self) -> WidgetDataModel:
        return WidgetDataModel(
            value=self.toPlainText(),
            type=StandardTypes.TEXT,
        )

    def size_hint(self) -> tuple[int, int]:
        return 400, 300

    def is_modified(self) -> bool:
        return self._main_text_edit.is_modified()


class QDefaultHTMLEdit(QDefaultTextEdit):
    @classmethod
    def from_model(cls, model: WidgetDataModel) -> QDefaultTextEdit:
        self = cls()
        self.initPlainText(model.value)
        if model.source is not None:
            self.setObjectName(model.source.name)
            # set default language
        self._footer._language_combobox.setCurrentText("HTML")
        self._footer._emit_language_changed()
        return self

    def to_model(self) -> WidgetDataModel:
        return WidgetDataModel(
            value=self.toPlainText(),
            type=StandardTypes.HTML,
        )
