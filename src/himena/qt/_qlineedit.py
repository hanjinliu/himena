from __future__ import annotations
import operator
from decimal import Decimal

from qtpy import QtWidgets as QtW, QtGui, QtCore
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
    valueChanged = QtCore.Signal(str)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setValidator(self._validator_class(self))
        self.textChanged.connect(self._on_text_changed)
        self.editingFinished.connect(self._on_editing_finished)
        self._empty_allowed = True
        self._last_acceptable_value = ""

    def _on_text_changed(self, text: str):
        state, text, _ = self.validator().validate(text, 0)
        if state == QtGui.QValidator.State.Acceptable:
            if text == "" and not self._empty_allowed:
                return
            self._last_acceptable_value = text
            self.valueChanged.emit(text)
        elif state == QtGui.QValidator.State.Intermediate:
            if text == "" and not self._empty_allowed:
                return

    def _on_editing_finished(self):
        text = self.text()
        validate_result = self.validator().validate(text, 0)
        if validate_result[0] == QtGui.QValidator.State.Acceptable:
            if text == "" and not self._empty_allowed:
                self.setText(self._last_acceptable_value)

    def empty_allowed(self) -> bool:
        return self._empty_allowed

    def set_empty_allowed(self, allowed: bool):
        self._empty_allowed = allowed
        self.setPlaceholderText("" if allowed else "required")

    def sizeHint(self) -> QtCore.QSize:
        hint = super().sizeHint()
        hint.setWidth(100)  # numerical values do not need to be too wide
        return hint

    def stepUp(self, large: bool = False):
        raise NotImplementedError

    def stepDown(self, large: bool = False):
        raise NotImplementedError

    def wheelEvent(self, a0: QtGui.QWheelEvent | None) -> None:
        if a0 is not None:
            if a0.angleDelta().y() > 0:
                self.stepUp()
                a0.accept()
            elif a0.angleDelta().y() < 0:
                self.stepDown()
                a0.accept()
        # NOTE: should not call super().wheelEvent(a0), as it will scroll the parent.

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

    def minimum(self):
        return self.validator().bottom()

    def setMinimum(self, min_):
        self.validator().setBottom(min_)

    def maximum(self):
        return self.validator().top()

    def setMaximum(self, max_):
        self.validator().setTop(max_)

    def validator(self) -> QIntOrNoneValidator | QDoubleOrNoneValidator:
        return super().validator()


class QIntLineEdit(QValuedLineEdit):
    _validator_class = QIntOrNoneValidator

    def stepUp(self, large: bool = False):
        text = self.text()
        if text == "":
            return None
        val = int(text)
        diff: int = 100 if large else 1
        self.setText(str(min(val + diff, self.validator().top())))

    def stepDown(self, large: bool = False):
        text = self.text()
        if text == "":
            return None
        val = int(text)
        diff: int = 100 if large else 1
        self.setText(str(max(val - diff, self.validator().bottom())))


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
                exp_ = op(exp_dec, diff)
                if (
                    Decimal(val_text) * 10**exp_ > self.validator().top()
                    or Decimal(val_text) * 10**exp_ < self.validator().bottom()
                ):
                    return None
                self.setText(val_text + "e" + str(exp_))
            else:
                val_min = self.validator().bottom() / 10 ** int(exp_text)
                val_max = self.validator().top() / 10 ** int(exp_text)
                val_dec = Decimal(val_text)
                diff = self._calc_diff(val_dec, False)
                val = op(val_dec, diff)
                val = max(min(val, val_max), val_min)
                self.setText(str(val) + "e" + exp_text)
        else:
            dec = Decimal(text)
            diff = self._calc_diff(dec, large)
            val = op(dec, diff)
            val = max(min(val, self.validator().top()), self.validator().bottom())
            self.setText(str(val))

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
