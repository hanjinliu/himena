from __future__ import annotations
from functools import partial
import inspect
from types import FunctionType
from typing import Any, Callable
import ast
from inspect import getsource

from qtpy import QtWidgets as QtW, QtCore, QtGui

from himena.consts import StandardType, MonospaceFontFamily
from himena.plugins import validate_protocol
from himena.standards.model_meta import FunctionMeta
from himena.types import WidgetDataModel
from himena.style import Theme
from ._text_base import QMainTextEdit


class QFunctionEdit(QtW.QWidget):
    """Widget for a Python function.

    A function can be compiled from a text edit widget.
    """

    __himena_widget_id__ = "builtins:QFunctionEdit"
    __himena_display_name__ = "Built-in Function Editor"

    def __init__(self):
        super().__init__()
        layout = QtW.QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        _label = "<code>f(x) = </code>"
        layout.addWidget(QtW.QLabel(_label))

        self._main_text_edit = QMainTextEdit()
        self._main_text_edit.setReadOnly(True)
        layout.addWidget(self._main_text_edit)

        self._parameter_edit = QtW.QWidget()
        self._parameter_layout = QtW.QFormLayout(self._parameter_edit)
        self._parameter_layout.setContentsMargins(0, 0, 0, 0)
        self._parameter_widgets: list[QPythonLiteralLineEdit] = []
        layout.addWidget(self._parameter_edit)

        self._model_type = StandardType.FUNCTION
        self._func_orig: Callable | None = None
        self._has_source_code = False
        self._control = QFunctionEditControl()

    @validate_protocol
    def update_model(self, model: WidgetDataModel):
        if not callable(func := model.value):
            raise TypeError(f"Input value must be callable, got {type(func)}.")
        if isinstance(func, partial):
            self._pfunc = func
            _func = func.func
            _func_orig = func
            args = func.args
            keywords = func.keywords
            sig = inspect.signature(func)
            bound = sig.bind_partial(*args, **keywords)
            for _ in range(len(bound.arguments) - self._parameter_layout.count()):
                edit = QPythonLiteralLineEdit()
                self._parameter_layout.addRow(edit)
                self._parameter_widgets.append(edit)
            for _ in range(self._parameter_layout.count() - len(bound.arguments)):
                self._parameter_layout.takeAt(0)
                self._parameter_widgets.pop(0)
            for ith, (key, value) in enumerate(bound.arguments.items()):
                edit = self._parameter_widgets[ith]
                edit.setLabel(key)
                edit.setValue(value)
        else:
            _func = _func_orig = func
        # try to get the source
        code_text: str | None = None
        if isinstance(meta := model.metadata, FunctionMeta):
            code_text = meta.source_code
        if code_text is None and isinstance(_func, FunctionType):
            try:
                code_text = getsource(_func)
            except Exception:
                # local function etc.
                code_text = None
        self._func_orig = _func_orig
        if code_text:
            self._main_text_edit.setPlainText(code_text)
            self._main_text_edit.syntax_highlight("python")
            self._has_source_code = True
        else:
            self._main_text_edit.setPlainText(repr(_func))
            self._main_text_edit.syntax_highlight(None)
            self._has_source_code = False
        self._control._type_label.setText(_function_type_repr(_func_orig))
        return None

    @validate_protocol
    def to_model(self) -> WidgetDataModel:
        if self._has_source_code:
            code = self._main_text_edit.toPlainText()
        else:
            code = None
        return WidgetDataModel(
            value=self._func_orig,
            type=self.model_type(),
            metadata=FunctionMeta(source_code=code),
        )

    @validate_protocol
    def model_type(self) -> str:
        return self._model_type

    @validate_protocol
    def control_widget(self) -> QtW.QWidget:
        return self._control

    @validate_protocol
    def is_editable(self) -> bool:
        return self._parameter_edit.isEnabled()

    @validate_protocol
    def set_editable(self, editable: bool):
        return self._parameter_edit.setEnabled(editable)

    @validate_protocol
    def size_hint(self) -> tuple[int, int]:
        return 280, 200 + 28 * self._parameter_layout.count()

    @validate_protocol
    def theme_changed_callback(self, theme: Theme):
        text_edit = self._main_text_edit
        if theme.is_light_background():
            text_edit._code_theme = "default"
        else:
            text_edit._code_theme = "native"
        text_edit.syntax_highlight(text_edit._language)

    def setFocus(self):
        self._main_text_edit.setFocus()


class QFunctionEditControl(QtW.QWidget):
    def __init__(self):
        super().__init__()
        layout = QtW.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._type_label = QtW.QLabel("")
        self._type_label.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter
        )
        layout.addWidget(QtW.QWidget(), 10)
        layout.addWidget(self._type_label)


class QPythonLiteralLineEdit(QtW.QWidget):
    """Line edit in param_name = XYZ format"""

    def __init__(self):
        super().__init__()
        layout = QtW.QHBoxLayout(self)
        layout.setContentsMargins(3, 0, 3, 0)
        self._label = QtW.QLabel("")
        self._label.setFixedWidth(60)
        self._label.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter
        )
        layout.addWidget(self._label)
        self._value_edit = QtW.QLineEdit()
        layout.addWidget(self._value_edit)
        self.setFont(QtGui.QFont(MonospaceFontFamily))

    def value(self) -> Any | None:
        text = self._value_edit.text().strip()
        if text == "":
            return None
        return ast.literal_eval(text)

    def setValue(self, value: Any | None):
        if value is None:
            self._value_edit.setText("")
        else:
            self._value_edit.setText(repr(value))

    def label(self) -> str:
        return self._label.text()

    def setLabel(self, label: str):
        self._label.setText(label + " = ")


def _function_type_repr(f) -> str:
    if isinstance(f, partial):
        return f"functools.partial of {_function_type_repr(f.func)}"
    ftype = type(f)
    return f"{ftype.__module__}.{ftype.__name__}"
