from __future__ import annotations
from typing import TYPE_CHECKING, Generic, TypeVar, cast

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
    QValuedLineEdit,
)

__all__ = ["IntEdit", "FloatEdit"]


class QBaseRangedStringWidget(QBaseStringWidget):
    def _mgui_get_min(self) -> float:
        """Get the minimum possible value."""
        val = self._qwidget.minimum()
        return val

    def _mgui_set_min(self, value: float):
        """Set the minimum possible value."""
        self._qwidget.setMinimum(value)

    def _mgui_get_max(self) -> float:
        """Set the maximum possible value."""
        return self._qwidget.maximum()

    def _mgui_set_max(self, value: float):
        """Set the maximum possible value."""
        self._qwidget.setMaximum(value)


_T = TypeVar("_T")


class RangedLineEdit(LineEdit, Generic[_T]):
    if TYPE_CHECKING:
        _widget: QBaseRangedStringWidget

    def __init__(
        self,
        value=Undefined,
        min=Undefined,
        max=Undefined,
        widget_type=None,
        **kwargs,
    ):
        app = use_app()
        assert app.native
        ValueWidget.__init__(
            self,
            value=value,
            widget_type=widget_type,
            **kwargs,
        )
        if min is not Undefined:
            self.min = min
        if max is not Undefined:
            self.max = max
        self._set_nullable(self._nullable)

    @property
    def min(self) -> _T:
        return self._widget._mgui_get_min()

    @min.setter
    def min(self, value: _T):
        self._widget._mgui_set_min(value)

    @property
    def max(self) -> _T:
        return self._widget._mgui_get_max()

    @max.setter
    def max(self, value: _T):
        self._widget._mgui_set_max(value)

    def _set_nullable(self, nullable: bool):
        qwidget = cast(QValuedLineEdit, self._widget._qwidget)
        qwidget.set_empty_allowed(nullable)


class QIntEdit(QBaseRangedStringWidget):
    _qwidget: QIntLineEdit

    def __init__(self, **kwargs) -> None:
        super().__init__(QIntLineEdit, "text", "setText", "valueChanged", **kwargs)

    def _post_get_hook(self, value):
        if value == "":
            return None
        return int(value)

    def _pre_set_hook(self, value):
        return str(value)


class IntEdit(RangedLineEdit):
    """Line edit for integer values."""

    def __init__(
        self,
        value=Undefined,
        min=Undefined,
        max=Undefined,
        **kwargs,
    ):
        super().__init__(
            value=value,
            min=min,
            max=max,
            widget_type=QIntEdit,
            **kwargs,
        )

    def get_value(self) -> int:
        val = super().get_value()
        if val is None and not self._nullable:
            raise ValueError(f"Must specify a value for {self.label!r}")
        return val

    def set_value(self, value):
        if value is None:
            if not self._nullable:
                raise ValueError(f"Value for {self.label} cannot be None")
            value = ""
        super().set_value(value)


class QFloatEdit(QBaseRangedStringWidget):
    _qwidget: QDoubleLineEdit

    def __init__(self, **kwargs) -> None:
        super().__init__(QDoubleLineEdit, "text", "setText", "valueChanged", **kwargs)

    def _post_get_hook(self, value):
        if value == "":
            return None
        return float(value)

    def _pre_set_hook(self, value):
        return str(value)


class FloatEdit(RangedLineEdit):
    def __init__(
        self,
        value=Undefined,
        min=Undefined,
        max=Undefined,
        **kwargs,
    ):
        super().__init__(
            value=value,
            min=min,
            max=max,
            widget_type=QFloatEdit,
            **kwargs,
        )

    def get_value(self) -> float:
        val = super().get_value()
        if val is None and not self._nullable:
            raise ValueError(f"Must specify a value for {self.label}")
        return val

    def set_value(self, value):
        if value is None:
            if not self._nullable:
                raise ValueError(f"Value for {self.label} cannot be None")
            value_str = ""
        else:
            value_str = float_to_str(value)
        super().set_value(value_str)


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
        kwargs["widget_type"] = QIntListEdit
        ValueWidget.__init__(
            self,
            value=value,
            **kwargs,
        )

    def get_value(self) -> list[int]:
        val = super().get_value()
        if val is None and not self._nullable:
            raise ValueError(f"Must specify a value for {self.label}")
        if val.strip() == "":
            return []
        return [int(part) for part in val.split(",")]

    def set_value(self, value):
        if value is None:
            if not self._nullable:
                raise ValueError(f"Value for {self.label} cannot be None")
            value_str = ""
        else:
            value_str = ", ".join(str(part) for part in value)
        super().set_value(value_str)


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
        kwargs["widget_type"] = QFloatListEdit
        ValueWidget.__init__(
            self,
            value=value,
            **kwargs,
        )

    def get_value(self) -> list[float]:
        val = super().get_value()
        if val is None and not self._nullable:
            raise ValueError(f"Must specify a value for {self.label}")
        if val.strip() == "":
            return []
        return [float(part) for part in val.split(",")]

    def set_value(self, value):
        if value is None:
            if not self._nullable:
                raise ValueError(f"Value for {self.label} cannot be None")
            value_str = ""
        else:
            value_str = ", ".join(float_to_str(part) for part in value)
        super().set_value(value_str)


def float_to_str(value: int | float):
    if isinstance(value, int) or hasattr(value, "__index__"):
        value_str = str(value)
        if len(value_str) > 5:
            value_str = format(value, ".8g")
        return value_str
    out = format(value, ".8g")
    if "." not in out and "e" not in out:
        return f"{out}.0"
    return out
