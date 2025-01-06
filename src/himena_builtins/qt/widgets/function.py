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
        self._main_text_edit.setReadOnly(True)
        layout.addWidget(self._main_text_edit)
        self._model_type = StandardType.FUNCTION
        self._func: Callable | None = None
        self._has_source_code = False
        self._control = QFunctionEditControl()

    @validate_protocol
    def update_model(self, model: WidgetDataModel):
        if not callable(func := model.value):
            raise TypeError(f"Input value must be callable, got {type(func)}.")
        # try to ge the source
        code_text: str | None = None
        if isinstance(meta := model.metadata, FunctionMeta):
            code_text = meta.source_code
        elif isinstance(model.value, FunctionType):
            code_text = getsource(model.value)
        self._func = func
        if code_text:
            self._main_text_edit.setPlainText(code_text)
            self._main_text_edit.syntax_highlight("python")
            self._has_source_code = True
        else:
            self._main_text_edit.setPlainText(repr(func))
            self._main_text_edit.syntax_highlight(None)
            self._has_source_code = False
        self._control._type_label.setText(_function_type_repr(func))
        return None

    @validate_protocol
    def to_model(self) -> Callable:
        if self._has_source_code:
            code = self._main_text_edit.toPlainText()
        return WidgetDataModel(
            value=self._func,
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
    def size_hint(self) -> tuple[int, int]:
        return 280, 200

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


class QPartialFunctionEdit(QtW.QWidget):
    def __init__(self):
        super().__init__()
        self._pfunc: partial | None = None
        self._function_edit = QFunctionEdit()
        self._parameter_edit = QtW.QWidget()
        self._parameter_layout = QtW.QFormLayout(self._parameter_edit)
        self._parameter_layout.setContentsMargins(0, 0, 0, 0)
        self._parameter_widgets: list[QPythonLiteralLineEdit] = []
        self._model_type = StandardType.FUNCTION_PARTIAL
        layout = QtW.QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.addWidget(self._function_edit)
        layout.addWidget(self._parameter_edit)
        self._control = QFunctionEditControl()

    @validate_protocol
    def update_model(self, model: WidgetDataModel):
        pfunc = model.value
        if not isinstance(pfunc, partial):
            raise ValueError(f"Value must be a partial function, got {type(pfunc)}.")
        self._model_type = model.type
        self._pfunc = pfunc
        func = pfunc.func
        args = pfunc.args
        keywords = pfunc.keywords
        self._function_edit.update_model(
            WidgetDataModel(value=func, type=StandardType.FUNCTION)
        )
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
        self._control._type_label.setText(
            "functools.partial of " + _function_type_repr(func)
        )
        return None

    @validate_protocol
    def to_model(self):
        return WidgetDataModel(
            value=self._pfunc,
            type=self.model_type(),
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
        return 280, 320


class QPythonLiteralLineEdit(QtW.QWidget):
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
        self._label.setText(label)


def _function_type_repr(f) -> str:
    ftype = type(f)
    return f"{ftype.__module__}.{ftype.__name__}"
