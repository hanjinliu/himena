from __future__ import annotations
from types import FunctionType
from typing import Callable
import ast
from inspect import getsource

from qtpy import QtWidgets as QtW, QtCore

from himena.consts import StandardType
from himena.plugins import validate_protocol
from himena.types import WidgetDataModel
from himena.style import Theme
from ._text_base import QMainTextEdit


class QFunctionEdit(QtW.QWidget):
    """Widget for defining a Python function.

    Note that the name space of this code is isolated from the main namespace.
    Technically, the content of this widget is just an independent .py file.
    """

    __himena_widget_id__ = "builtins:QFunctionEdit"
    __himena_display_name__ = "Built-in Function Editor"

    def __init__(self):
        super().__init__()
        layout = QtW.QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        self._main_text_edit = QMainTextEdit()
        self._edit_btn = QtW.QPushButton("OK")
        self._edit_btn.setFixedWidth(50)
        self._main_text_edit.syntax_highlight("python")
        layout.addWidget(self._main_text_edit)
        layout.addWidget(self._edit_btn, alignment=QtCore.Qt.AlignmentFlag.AlignRight)
        self._model_type = StandardType.FUNCTION
        self._current_code = ""
        self._edit_btn.clicked.connect(self._on_edit_btn_clicked)

    @validate_protocol
    def update_model(self, model: WidgetDataModel):
        if isinstance(model.value, FunctionType):
            code_text = getattr(model.value, "__source_code__", None) or getsource(
                model.value
            )
        elif isinstance(model.value, str):
            ast.parse(model.value)  # dry run
            code_text = model.value
        elif callable(model.value):
            raise NotImplementedError("Only FunctionType is supported.")
        else:
            raise ValueError(
                f"Value must be a function or a string, got {type(model.value)}."
            )
        self._main_text_edit.setPlainText(code_text)
        self._set_current_code(code_text)
        self._set_editing(False)
        return None

    @validate_protocol
    def to_model(self) -> Callable:
        code = self._current_code
        mod = ast.parse(code)
        global_vars = {}
        local_vars = {}
        out = None
        nblock = len(mod.body)
        filename = "<QFunctionEdit>"
        if nblock == 0:
            raise ValueError("Code is empty.")
        if nblock == 1 and isinstance(mod.body[0], ast.FunctionDef):
            exec(compile(mod, filename, "exec"), global_vars, local_vars)
            out = local_vars[mod.body[0].name]
        else:
            for idx, block in enumerate(mod.body):
                if idx == nblock - 1:
                    out = eval(
                        compile(block, filename, "eval"), global_vars, local_vars
                    )
                else:
                    exec(compile(block, filename, "exec"), global_vars, local_vars)
        if not callable(out):
            raise ValueError("Code does not define a callable object.")
        # this is needed for the function to be editable by other QFunctionEdit
        out.__source_code__ = code
        return WidgetDataModel(value=out, type=self.model_type())

    @validate_protocol
    def model_type(self) -> str:
        return self._model_type

    @validate_protocol
    def size_hint(self) -> tuple[int, int]:
        return 280, 320

    @validate_protocol
    def theme_changed_callback(self, theme: Theme):
        text_edit = self._main_text_edit
        if theme.is_light_background():
            text_edit._code_theme = "default"
        else:
            text_edit._code_theme = "native"
        text_edit.syntax_highlight(text_edit._language)

    @validate_protocol
    def is_editable(self) -> bool:
        return self._edit_btn.isEnabled()

    @validate_protocol
    def set_editable(self, editable: bool):
        if not editable:
            self._set_editing(False)
        self._edit_btn.setEnabled(editable)

    def setFocus(self):
        self._main_text_edit.setFocus()

    def _on_edit_btn_clicked(self):
        if self._edit_btn.text() == "OK":
            code = self._main_text_edit.toPlainText()
            self._set_current_code(code)
            self._set_editing(False)
        else:
            self._set_editing(True)
            self._main_text_edit.setFocus()

    def _set_editing(self, editing: bool):
        if editing:
            self._edit_btn.setText("OK")
            self._main_text_edit.setReadOnly(False)
        else:
            self._edit_btn.setText("Edit")
            self._main_text_edit.setReadOnly(True)
        return

    def _set_current_code(self, code: str):
        ast.parse(code)  # dry run
        self._current_code = code
        return
