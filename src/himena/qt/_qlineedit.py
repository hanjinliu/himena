from __future__ import annotations
import operator
from decimal import Decimal

from qtpy import QtWidgets as QtW, QtGui
from qtpy.QtCore import Qt


class QIntOrNoneValidator(QtGui.QIntValidator):
    """Validator that accepts '' as None, and otherwise behaves as QIntValidator."""

    def validate(
        self,
        a0: str | None,
        a1: int,
    ) -> tuple[QtGui.QValidator.State, str, int]:
        if a0 == "":
            return QtGui.QValidator.State.Acceptable, "", a1
        return super().validate(a0, a1)


class QDoubleOrNoneValidator(QtGui.QDoubleValidator):
    """Validator that accepts '' as None, and otherwise behaves as QDoubleValidator."""

    def validate(
        self,
        a0: str | None,
        a1: int,
    ) -> tuple[QtGui.QValidator.State, str, int]:
        if a0 == "":
            return QtGui.QValidator.State.Acceptable, "", a1
        return super().validate(a0, a1)


class QCommaSeparatedValidator(QtGui.QValidator):
    _ChildValidator: QtGui.QValidator

    def validate(
        self,
        a0: str | None,
        a1: int,
    ) -> tuple[QtGui.QValidator.State, str, int]:
        if a0 == "" or a0 is None:
            return QtGui.QValidator.State.Acceptable, "", a1
        if a0.strip().endswith(","):
            if a0.strip().endswith(",,"):
                return QtGui.QValidator.State.Invalid, a0, a1
            return QtGui.QValidator.State.Intermediate, a0, a1
        state_list = [
            self._ChildValidator.validate(part.strip(), 0)[0] for part in a0.split(",")
        ]
        is_valid = all(
            state == QtGui.QValidator.State.Acceptable for state in state_list
        )
        is_intermediate = all(
            state != QtGui.QValidator.State.Invalid for state in state_list
        )
        if is_valid:
            return QtGui.QValidator.State.Acceptable, a0, a1
        if is_intermediate:
            return QtGui.QValidator.State.Intermediate, a0, a1
        return QtGui.QValidator.State.Invalid, a0, a1


class QCommaSeparatedIntValidator(QCommaSeparatedValidator):
    _ChildValidator = QtGui.QIntValidator()


class QCommaSeparatedDoubleValidator(QCommaSeparatedValidator):
    _ChildValidator = QtGui.QDoubleValidator()


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


class QCommaSeparatedIntLineEdit(QtW.QLineEdit):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setValidator(QCommaSeparatedIntValidator(self))


class QCommaSeparatedDoubleLineEdit(QtW.QLineEdit):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setValidator(QCommaSeparatedDoubleValidator(self))
