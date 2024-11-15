from __future__ import annotations

from magicgui.widgets import LineEdit
from magicgui.widgets.bases import ValueWidget
from magicgui.types import Undefined
from magicgui.application import use_app
from magicgui.backends._qtpy.widgets import QBaseStringWidget
from himena.qt._qlineedit import (
    QIntLineEdit,
    QDoubleLineEdit,
    QCommaSeparatedIntLineEdit,
    QCommaSeparatedDoubleLineEdit,
)

__all__ = ["IntEdit", "FloatEdit"]


class QIntEdit(QBaseStringWidget):
    _qwidget: QIntLineEdit

    def __init__(self, **kwargs) -> None:
        super().__init__(QIntLineEdit, "text", "setText", "textChanged", **kwargs)

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
            raise ValueError(f"Must specify a value for {self.label!r}")
        return val

    @LineEdit.value.setter
    def value(self, value):
        if value is None:
            if not self._nullable:
                raise ValueError(f"Value for {self.label} cannot be None")
            value = ""
        LineEdit.value.fset(self, value)


class QFloatEdit(QBaseStringWidget):
    _qwidget: QDoubleLineEdit

    def __init__(self, **kwargs) -> None:
        super().__init__(QDoubleLineEdit, "text", "setText", "textChanged", **kwargs)

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
        if value is None:
            if not self._nullable:
                raise ValueError(f"Value for {self.label} cannot be None")
            value_str = ""
        else:
            value_str = float_to_str(value)
        LineEdit.value.fset(self, value_str)


class QIntListEdit(QBaseStringWidget):
    _qwidget: QCommaSeparatedIntLineEdit

    def __init__(self, **kwargs) -> None:
        super().__init__(
            QCommaSeparatedIntLineEdit, "text", "setText", "textChanged", **kwargs
        )


class IntListEdit(LineEdit):
    def __init__(self, value=Undefined, **kwargs):
        app = use_app()
        assert app.native
        ValueWidget.__init__(
            self,
            value=value,
            widget_type=QIntListEdit,
            **kwargs,
        )

    def get_value(self) -> list[int]:
        val = super().get_value()
        if val is None and not self._nullable:
            raise ValueError(f"Must specify a value for {self.label}")
        if val.strip() == "":
            return []
        return [int(part) for part in val.split(",")]

    @LineEdit.value.setter
    def value(self, value):
        if value is None:
            value_str = ""
        else:
            value_str = ", ".join(str(part) for part in value)
        LineEdit.value.fset(self, value_str)


class QFloatListEdit(QBaseStringWidget):
    _qwidget: QCommaSeparatedDoubleLineEdit

    def __init__(self, **kwargs) -> None:
        super().__init__(
            QCommaSeparatedDoubleLineEdit, "text", "setText", "textChanged", **kwargs
        )


class FloatListEdit(LineEdit):
    def __init__(self, value=Undefined, **kwargs):
        app = use_app()
        assert app.native
        ValueWidget.__init__(
            self,
            value=value,
            widget_type=QFloatListEdit,
            **kwargs,
        )

    def get_value(self) -> list[float]:
        val = super().get_value()
        if val is None and not self._nullable:
            raise ValueError(f"Must specify a value for {self.label}")
        if val.strip() == "":
            return []
        return [float(part) for part in val.split(",")]

    @LineEdit.value.setter
    def value(self, value):
        if value is None:
            value_str = ""
        else:
            value_str = ",".join(float_to_str(part) for part in value)
        LineEdit.value.fset(self, value_str)


def float_to_str(value: int | float):
    if isinstance(value, int) or hasattr(value, "__index__"):
        value_str = str(value)
        if len(value_str) > 5:
            value_str = format(value, ".8g")
        return value_str
    out = format(value, ".8g")
    if "." not in out:
        return f"{out}.0"
    return out
