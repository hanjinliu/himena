from __future__ import annotations

from typing import Iterator

from qtpy import QtWidgets as QtW
from qtpy import QtGui, QtCore

from himena.consts import MonospaceFontFamily
from himena.qt._qfinderwidget import QFinderWidget
from himena.widgets import current_instance
from himena.utils.misc import is_absolute_file_path_string, is_url_string

POINT_SIZES: list[int] = [5, 6, 7, 8, 9, 10, 11, 12, 14, 16, 18, 20, 24, 28, 32, 36, 40, 48, 56, 64, 72]  # fmt: skip
TAB_SIZES: list[int] = [1, 2, 3, 4, 5, 6, 7, 8]


class QMainTextEdit(QtW.QPlainTextEdit):
    def __init__(self, parent: QtW.QWidget | None = None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setWordWrapMode(QtGui.QTextOption.WrapMode.NoWrap)
        font = QtGui.QFont(MonospaceFontFamily, 10)
        self._default_font = font
        self.setFont(font)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setTabStopDistance(self.fontMetrics().horizontalAdvance(" ") * 4)
        self._tab_size = 4
        self._highlight = None
        self._language = "Plain Text"
        self._code_theme = "default"
        self._finder_widget: QFinderWidget | None = None

    def is_modified(self) -> bool:
        return self.document().isModified()

    def syntax_highlight(self, lang: str | None = None):
        """Highlight syntax."""
        self._language = lang
        if lang is None or lang == "Plain Text":
            if self._highlight is not None:
                self._highlight.setDocument(None)
            return None
        from superqt.utils import CodeSyntaxHighlight

        highlight = CodeSyntaxHighlight(self.document(), lang, theme=self._code_theme)
        self._highlight = highlight

    def tab_size(self):
        return self._tab_size

    def set_tab_size(self, size: int):
        self._tab_size = size
        self.setTabStopDistance(self.fontMetrics().horizontalAdvance(" ") * size)

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
                    text = clip.text().replace("\n\t", "\n" + " " * self.tab_size())
                    cursor = self.textCursor()
                    cursor.insertText(text)
                    return True
                elif (
                    _key == QtCore.Qt.Key.Key_Comma
                    and _mod & QtCore.Qt.KeyboardModifier.ControlModifier
                    and _mod & QtCore.Qt.KeyboardModifier.ShiftModifier
                ) or (
                    _key == QtCore.Qt.Key.Key_Greater
                    and _mod & QtCore.Qt.KeyboardModifier.ControlModifier
                ):
                    self.setFont(change_point_size(self.font(), 1))
                    return True
                elif (
                    _key == QtCore.Qt.Key.Key_Period
                    and _mod & QtCore.Qt.KeyboardModifier.ControlModifier
                    and _mod & QtCore.Qt.KeyboardModifier.ShiftModifier
                ) or (
                    _key == QtCore.Qt.Key.Key_Less
                    and _mod & QtCore.Qt.KeyboardModifier.ControlModifier
                ):
                    self.setFont(change_point_size(self.font(), -1))
                    return True
                elif (
                    _key == QtCore.Qt.Key.Key_0
                    and _mod & QtCore.Qt.KeyboardModifier.ControlModifier
                ):
                    self.setFont(self._default_font)
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

    def _find_string(self):
        if self._finder_widget is None:
            self._finder_widget = QFinderWidget(self)
        self._finder_widget.show()
        self._align_finder()

    def resizeEvent(self, event):
        if self._finder_widget is not None:
            self._align_finder()
        super().resizeEvent(event)

    def _align_finder(self):
        if fd := self._finder_widget:
            vbar = self.verticalScrollBar()
            if vbar.isVisible():
                fd.move(self.width() - fd.width() - vbar.width() - 3, 5)
            else:
                fd.move(self.width() - fd.width() - 3, 5)

    def mouseMoveEvent(self, e: QtGui.QMouseEvent):
        """Change cursor to pointing hand when hovering over URLs"""
        if (
            e.modifiers() & QtCore.Qt.KeyboardModifier.ControlModifier
        ) and self._url_under_pos(e.pos()):
            self.viewport().setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        else:
            self.viewport().setCursor(QtCore.Qt.CursorShape.IBeamCursor)
        return super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        if (e.modifiers() & QtCore.Qt.KeyboardModifier.ControlModifier) and (
            part := self._url_under_pos(e.pos())
        ):
            if is_url_string(part):
                QtGui.QDesktopServices.openUrl(QtCore.QUrl(part))
                return
            elif is_absolute_file_path_string(part):
                current_instance().read_file(part)  # open URL
                return
        return super().mouseReleaseEvent(e)

    def _url_under_pos(self, pos: QtCore.QPoint) -> str | None:
        cursor = self.cursorForPosition(pos)
        cursor.select(QtGui.QTextCursor.SelectionType.WordUnderCursor)

        # Get the full line to check for URLs
        text_cursor = self.textCursor()
        text_cursor.setPosition(cursor.selectionStart())
        text_cursor.movePosition(QtGui.QTextCursor.MoveOperation.StartOfLine)
        text_cursor.movePosition(
            QtGui.QTextCursor.MoveOperation.EndOfLine,
            QtGui.QTextCursor.MoveMode.KeepAnchor,
        )
        line = text_cursor.selectedText()

        # Check if we're hovering over a URL
        char_pos = cursor.positionInBlock()
        for part in line.split():
            if is_url_string(part) or is_absolute_file_path_string(part):
                start = line.index(part)
                end = start + len(part)
                if start <= char_pos <= end:
                    return part


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


def change_point_size(cur_font: QtGui.QFont, step: int) -> QtGui.QFont:
    current_size = cur_font.pointSize()
    nmax = len(POINT_SIZES)
    cur_idx = nmax - 1
    for idx, size in enumerate(POINT_SIZES):
        if current_size <= size:
            cur_idx = idx
            break
    next_idx = min(max(cur_idx + step, 0), nmax - 1)
    new_size = POINT_SIZES[next_idx]
    cur_font.setPointSize(new_size)
    return cur_font
