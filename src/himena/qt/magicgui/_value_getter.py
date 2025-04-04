from __future__ import annotations
from typing import Callable, TypeVar

from magicgui.widgets import LineEdit, PushButton, Label
from magicgui.widgets.bases import ValuedContainerWidget

_V = TypeVar("_V")


def _label(text: str, width: int) -> Label:
    label = Label(value=text)
    label.max_width = width
    return label


class SliderRangeGetter(ValuedContainerWidget[tuple[_V, _V]]):
    """Widget to get a min and max value from an array widget."""

    def __init__(
        self,
        getter: Callable[[], _V],
        **kwargs,
    ):
        self._value_min = LineEdit()
        self._value_max = LineEdit()
        self._get_value_btn_min = PushButton(text="Read")
        self._get_value_btn_max = PushButton(text="Read")
        self._getter = getter
        self._value_min.max_width = 50
        self._value_max.max_width = 50
        self._get_value_btn_min.max_width = 40
        self._get_value_btn_max.max_width = 40

        super().__init__(
            widgets=[
                _label("min", 24),
                self._value_min,
                self._get_value_btn_min,
                _label("max", 24),
                self._value_max,
                self._get_value_btn_max,
            ],
            labels=False,
            layout="horizontal",
            **kwargs,
        )

        self._value_min.changed.connect(self._on_value_changed)
        self._get_value_btn_min.changed.connect(self._on_min_press)
        self._get_value_btn_max.changed.connect(self._on_max_press)
        self.margins = (0, 0, 0, 0)

    def _on_min_press(self):
        self._value_min.value = str(self._getter())

    def _on_max_press(self):
        self._value_max.value = str(self._getter())

    def _on_value_changed(self):
        self.changed.emit(self.get_value())

    def get_value(self) -> tuple[_V, _V]:
        if self._value_min.value.strip() == "":
            _value_min = None
        else:
            _value_min = int(self._value_min.value)
        if self._value_max.value.strip() == "":
            _value_max = None
        else:
            _value_max = int(self._value_max.value) + 1
        return (_value_min, _value_max)

    def set_value(self, value: tuple[_V, _V]):
        if value[0] is None:
            self._value_min.value = ""
        else:
            self._value_min.value = repr(value[0])
        if value[1] is None:
            self._value_max.value = ""
        else:
            # The max value is exclusive, so we need to subtract 1
            self._value_max.value = repr(value[1] - 1)
