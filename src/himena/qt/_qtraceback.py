from __future__ import annotations

import re
import sys
from typing import Callable, Generator, TYPE_CHECKING
import weakref

import numpy as np
from qtpy import QtWidgets as QtW, QtGui, QtCore
from psygnal import EmitLoopError

from himena.consts import MonospaceFontFamily
from himena.utils.misc import ansi2html

if TYPE_CHECKING:
    from types import TracebackType
    from warnings import WarningMessage
    from himena.qt._qmain_window import QMainWindow

    ExcInfo = tuple[type[BaseException], BaseException, TracebackType]


class QtTracebackDialog(QtW.QDialog):
    """A dialog box that shows Python traceback."""

    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Traceback")
        layout = QtW.QVBoxLayout()
        self.setLayout(layout)

        # prepare text edit
        self._text = QtW.QTextEdit(self)
        self._text.setReadOnly(True)
        self._text.setFontFamily(MonospaceFontFamily)
        self._text.setLineWrapMode(QtW.QTextEdit.LineWrapMode.NoWrap)
        layout.addWidget(self._text)

        self.resize(600, 400)

    def setText(self, text: str):
        """Always set text as a HTML text."""
        self._text.setHtml(text)

    def keyPressEvent(self, a0: QtGui.QKeyEvent) -> None:
        if (
            a0.modifiers() == QtCore.Qt.KeyboardModifier.ControlModifier
            and a0.key() in (QtCore.Qt.Key.Key_W, QtCore.Qt.Key.Key_Q)
        ):
            self.close()
        else:
            return super().keyPressEvent(a0)


class QtErrorMessageBox(QtW.QWidget):
    """An message box widget for displaying Python exception."""

    def __init__(
        self,
        text: str,
        exc: Exception | None,
        parent: QMainWindow,
    ):
        self._main_window = weakref.ref(parent)
        super().__init__()

        self._exc = exc
        self.text_edit = QtW.QPlainTextEdit(self)
        self.text_edit.setReadOnly(True)
        self.text_edit.setWordWrapMode(QtGui.QTextOption.WrapMode.WordWrap)
        self.text_edit.setVerticalScrollBarPolicy(
            QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self.text_edit.setHorizontalScrollBarPolicy(
            QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.text_edit.setPlainText(text)

        layout = QtW.QVBoxLayout(self)
        layout.addWidget(self.text_edit, stretch=100)

    def _traceback_button_clicked(self, *, runtime: bool = True):
        tb = self._get_traceback()
        dlg = QtTracebackDialog(self)
        dlg.setText(tb)
        focus = QtW.QApplication.focusWidget()
        if runtime:
            dlg.exec()
        if focus:
            focus.setFocus()

    def _enter_debugger_button_clicked(self):
        import pdb

        if hasattr(QtCore, "pyqtRemoveInputHook"):
            QtCore.pyqtRemoveInputHook()
        try:
            pdb.post_mortem(self._exc.__traceback__)
        finally:
            if hasattr(QtCore, "pyqtRestoreInputHook"):
                QtCore.pyqtRestoreInputHook()

    @classmethod
    def from_exc(cls, e: Exception, parent: QMainWindow):
        """Construct message box from a exception."""
        # unwrap EmitLoopError
        while isinstance(e, EmitLoopError):
            e = e.__cause__

        if len(e.args) > 0:
            text = f"{type(e).__name__}: {e}"
        else:
            text = ""
        self = cls(text, e, parent)

        # prepare buttons specific to Exception
        footer = QtW.QWidget()
        layout = QtW.QHBoxLayout(footer)
        layout.setContentsMargins(0, 0, 0, 0)

        traceback_button = QtW.QPushButton("Trackback", self)
        enter_debugger_button = QtW.QPushButton("Debug", self)
        traceback_button.setFixedHeight(20)
        enter_debugger_button.setFixedHeight(20)

        traceback_button.clicked.connect(self._traceback_button_clicked)
        enter_debugger_button.clicked.connect(self._enter_debugger_button_clicked)

        layout.addWidget(traceback_button)
        layout.addWidget(enter_debugger_button)
        layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        self.layout().addWidget(footer)
        return self

    @classmethod
    def from_warning(cls, w: WarningMessage, parent: QMainWindow):
        if isinstance(w.message, Warning):
            text = str(w.message)
            exc = w.message
        else:
            text = w.message
            exc = None
        self = cls(text, exc, parent)
        return self

    def _exc_info(self) -> ExcInfo:
        return (
            self._exc.__class__,
            self._exc,
            self._exc.__traceback__,
        )

    def _get_traceback(self) -> str:
        background = (
            self._main_window().palette().color(QtGui.QPalette.ColorRole.Window)
        )
        is_dark = background.lightnessF() < 0.5
        if self._exc is None:
            import traceback

            tb = traceback.format_exc()
        else:
            tb = get_tb_formatter()(self._exc_info(), as_html=True, is_dark=is_dark)
        return tb


# Following functions are mostly copied from napari (BSD 3-Clause).
# See https://github.com/napari/napari/blob/main/napari/utils/_tracebacks.py


def get_tb_formatter() -> Callable[[ExcInfo, bool, bool], str]:
    """Return a formatter callable that uses IPython VerboseTB if available.

    Imports IPython lazily if available to take advantage of ultratb.VerboseTB.
    If unavailable, cgitb is used instead, but this function overrides a lot of
    the hardcoded citgb styles and adds error chaining (for exceptions that
    result from other exceptions).

    Returns
    -------
    callable
        A function that accepts a 3-tuple and a boolean ``(exc_info, as_html)``
        and returns a formatted traceback string. The ``exc_info`` tuple is of
        the ``(type, value, traceback)`` format returned by sys.exc_info().
        The ``as_html`` determines whether the traceback is formatted in html
        or plain text.
    """
    try:
        import IPython.core.ultratb  # noqa: F401

        format_exc_info = format_exc_info_ipython

    except ModuleNotFoundError:  # pragma: no cover
        if sys.version_info < (3, 11):
            format_exc_info = format_exc_info_py310
        else:
            format_exc_info = format_exc_info_py311
    return format_exc_info


def _filter_traceback(tb: TracebackType) -> TracebackType:
    tb_orig = tb
    while tb:
        if tb.tb_next and tb.tb_next.tb_frame.f_locals.get("__tracebackhide__", False):
            tb.tb_next = None
            break
        tb = tb.tb_next
    return tb_orig


def format_exc_info_ipython(info: ExcInfo, as_html: bool, is_dark: bool = False) -> str:
    import IPython.core.ultratb

    typ, exc, tb = info
    color = "Neutral"
    tb = _filter_traceback(tb)

    # avoid verbose printing of the array data
    with np.printoptions(precision=5, threshold=10, edgeitems=2):
        if IPython.version_info >= (9, 0):
            vbtb = IPython.core.ultratb.VerboseTB(theme_name=color.lower())
        else:
            vbtb = IPython.core.ultratb.VerboseTB(color_scheme=color)
        if as_html:
            ansi_string = (
                vbtb.text(typ, exc, tb)
                .replace(" ", "&nbsp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace("\n", "<br>")
            )
            _html = "".join(ansi2html(ansi_string, is_dark=is_dark))
            _html = (
                f"<span style='font-family: monaco,{MonospaceFontFamily},"
                "monospace;'>" + _html + "</span>"
            )
            tb_text = _html
        else:
            tb_text = vbtb.text(*info)
    return tb_text


# cgitb does not support error chaining...
# see https://peps.python.org/pep-3134/#enhanced-reporting
# this is a workaround
def cgitb_chain(exc: Exception) -> Generator[str, None, None]:
    """Recurse through exception stack and chain cgitb_html calls."""
    if exc.__cause__:
        yield from cgitb_chain(exc.__cause__)
        yield (
            '<br><br><font color="#51B432">The above exception was '
            "the direct cause of the following exception:</font><br>"
        )
    elif exc.__context__:
        yield from cgitb_chain(exc.__context__)
        yield (
            '<br><br><font color="#51B432">During handling of the '
            "above exception, another exception occurred:</font><br>"
        )
    yield cgitb_html(exc)


def cgitb_html(exc: Exception) -> str:
    """Format exception with cgitb.html."""
    import cgitb

    info = (type(exc), exc, exc.__traceback__)
    return cgitb.html(info)


def format_exc_info_py310(info: ExcInfo, as_html: bool, is_dark=False) -> str:
    import traceback

    # avoid verbose printing of the array data
    with np.printoptions(precision=5, threshold=10, edgeitems=2):
        if as_html:
            html = "\n".join(cgitb_chain(info[1]))
            # cgitb has a lot of hardcoded colors that don't work for us
            # remove bgcolor, and let theme handle it
            html = re.sub('bgcolor="#.*"', "", html)
            # remove superfluous whitespace
            html = html.replace("<br>\n", "\n")
            # but retain it around the <small> bits
            html = re.sub(r"(<tr><td><small.*</tr>)", "<br>\\1<br>", html)
            # weird 2-part syntax is a workaround for hard-to-grep text.
            html = html.replace(
                "<p>A problem occurred in a Python script.  Here is the sequence of",
                "",
            )
            html = html.replace(
                "function calls leading up to the error, "
                "in the order they occurred.</p>",
                "<br>",
            )
            # remove hardcoded fonts
            html = html.replace('face="helvetica, arial"', "")
            html = (
                "<span style='font-family: monaco,courier,monospace;'>"
                + html
                + "</span>"
            )
            tb_text = html
        else:
            # if we don't need HTML, just use traceback
            tb_text = "".join(traceback.format_exception(*info))
    return tb_text


def format_exc_info_py311(info: ExcInfo, as_html: bool, is_dark=False) -> str:
    import traceback

    # avoid verbose printing of the array data
    with np.printoptions(precision=5, threshold=10, edgeitems=2):
        tb_text = "".join(traceback.format_exception(*info))
        if as_html:
            tb_text = "<pre>" + tb_text + "</pre>"
    return tb_text
