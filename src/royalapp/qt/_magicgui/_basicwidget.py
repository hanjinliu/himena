from __future__ import annotations

from qtpy import QtWidgets as QtW
from magicgui.widgets import LineEdit
from magicgui.widgets.bases import ValueWidget
from magicgui.types import Undefined
from magicgui.application import use_app
from magicgui.backends._qtpy.widgets import LineEdit as BaseLineEdit

__all__ = ["IntEdit", "FloatEdit"]


class QIntEdit(BaseLineEdit):
    _qwidget: QtW.QLineEdit

    def _post_get_hook(self, value):
        if value == "":
            return None
        return int(value)

    def _pre_set_hook(self, value):
        return str(value)


class IntEdit(LineEdit):
    def __init__(self, value=Undefined, **kwargs):
        app = use_app()
        assert app.native
        ValueWidget.__init__(
            self,
            value=value,
            widget_type=QIntEdit,
            **kwargs,
        )

    def get_value(self) -> int:
        val = super().get_value()
        if val is None and not self._nullable:
            raise ValueError(f"Must specify a value for {self.label}")
        return val

    @LineEdit.value.setter
    def value(self, value):
        if value is None and not self._nullable:
            raise ValueError(f"Value for {self.label} cannot be None")
        LineEdit.value.fset(self, value)


class QFloatEdit(BaseLineEdit):
    _qwidget: QtW.QLineEdit

    def _post_get_hook(self, value):
        if value == "":
            return None
        return float(value)

    def _pre_set_hook(self, value):
        return str(value)


class FloatEdit(LineEdit):
    def __init__(self, value=Undefined, **kwargs):
        app = use_app()
        assert app.native
        ValueWidget.__init__(
            self,
            value=value,
            widget_type=QFloatEdit,
            **kwargs,
        )

    def get_value(self) -> float:
        val = super().get_value()
        if val is None and not self._nullable:
            raise ValueError(f"Must specify a value for {self.label}")
        return val

    @LineEdit.value.setter
    def value(self, value):
        if value is None and not self._nullable:
            raise ValueError(f"Value for {self.label} cannot be None")
        LineEdit.value.fset(self, value)
