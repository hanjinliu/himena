from __future__ import annotations
import operator
from decimal import Decimal

from qtpy import QtWidgets as QtW, QtGui
from qtpy.QtCore import Qt
from magicgui.widgets import LineEdit
from magicgui.widgets.bases import ValueWidget
from magicgui.types import Undefined
from magicgui.application import use_app
from magicgui.backends._qtpy.widgets import QBaseStringWidget

__all__ = ["IntEdit", "FloatEdit"]


class QIntOrNoneValidator(QtGui.QIntValidator):
    def validate(
        self,
        a0: str | None,
        a1: int,
    ) -> tuple[QtGui.QValidator.State, str, int]:
        if a0 == "":
            return QtGui.QValidator.State.Acceptable, "", a1
        return super().validate(a0, a1)


class QDoubleOrNoneValidator(QtGui.QDoubleValidator):
    def validate(
        self,
        a0: str | None,
        a1: int,
    ) -> tuple[QtGui.QValidator.State, str, int]:
        if a0 == "":
            return QtGui.QValidator.State.Acceptable, "", a1
        return super().validate(a0, a1)


class QValuedLineEdit(QtW.QLineEdit):
    _validator_class: type[QIntOrNoneValidator | QDoubleOrNoneValidator]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setValidator(self._validator_class(self))

    def stepUp(self, large: bool = False):
        raise NotImplementedError

    def stepDown(self, large: bool = False):
        raise NotImplementedError

    def wheelEvent(self, a0: QtGui.QWheelEvent | None) -> None:
        if a0 is not None:
            if a0.angleDelta().y() > 0:
                self.stepUp()
            elif a0.angleDelta().y() < 0:
                self.stepDown()
        return super().wheelEvent(a0)

    def keyPressEvent(self, a0: QtGui.QKeyEvent | None) -> None:
        if a0.modifiers() == Qt.KeyboardModifier.NoModifier:
            if a0.key() == Qt.Key.Key_Up:
                self.stepUp()
            elif a0.key() == Qt.Key.Key_PageUp:
                self.stepUp(large=True)
            elif a0.key() == Qt.Key.Key_Down:
                self.stepDown()
            elif a0.key() == Qt.Key.Key_PageDown:
                self.stepDown(large=True)
            else:
                return super().keyPressEvent(a0)
        else:
            return super().keyPressEvent(a0)


class QIntLineEdit(QValuedLineEdit):
    _validator_class = QIntOrNoneValidator

    def stepUp(self, large: bool = False):
        text = self.text()
        if text == "":
            return None
        val = int(text)
        diff: int = 100 if large else 1
        self.setText(str(val + diff))

    def stepDown(self, large: bool = False):
        text = self.text()
        if text == "":
            return None
        val = int(text)
        diff: int = 100 if large else 1
        self.setText(str(val - diff))


class QDoubleLineEdit(QValuedLineEdit):
    _validator_class = QDoubleOrNoneValidator

    def stepUp(self, large: bool = False):
        return self._step_up_or_down(large, operator.add)

    def stepDown(self, large: bool = False):
        return self._step_up_or_down(large, operator.sub)

    def _step_up_or_down(self, large: bool, op):
        text = self.text()
        if text == "":
            return None
        if "e" in text:
            val_text, exp_text = text.split("e")
            if large:
                exp_dec = Decimal(exp_text)
                diff = self._calc_diff(exp_dec, False)
                self.setText(val_text + "e" + str(op(exp_dec, diff)))
            else:
                val_dec = Decimal(val_text)
                diff = self._calc_diff(val_dec, False)
                self.setText(str(op(val_dec, diff)) + "e" + exp_text)
        else:
            dec = Decimal(text)
            diff = self._calc_diff(dec, large)
            self.setText(str(op(dec, diff)))

    def _calc_diff(self, dec: Decimal, large: bool):
        exponent = dec.as_tuple().exponent
        if not isinstance(exponent, int):
            return None
        ten = Decimal("10")
        diff = ten ** (exponent + 2) if large else ten**exponent
        return diff


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
        if value is None and not self._nullable:
            raise ValueError(f"Value for {self.label} cannot be None")
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
        if value is None and not self._nullable:
            raise ValueError(f"Value for {self.label} cannot be None")
        value_str = float_to_str(value)
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
