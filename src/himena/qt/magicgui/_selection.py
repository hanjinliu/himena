from __future__ import annotations

import re
from typing import Callable
from magicgui.types import Undefined
from magicgui.widgets import LineEdit, PushButton, Label
from magicgui.widgets.bases import ValuedContainerWidget

SLICE_PATTERN = re.compile(r"^\s*\d*\s*:\s*\d*\s*,\s*\d*\s*:\s*\d*\s*$")

SelectionType = tuple[tuple[int, int], tuple[int, int]]


class SelectionEdit(ValuedContainerWidget[SelectionType]):
    def __init__(
        self,
        value=Undefined,
        bind=Undefined,
        getter: Callable[[], SelectionType] | None = None,
        **kwargs,
    ):
        self._label_0 = Label(value="A[")
        self._line_edit = LineEdit()
        self._label_1 = Label(value="]")
        self._read_btn = PushButton(text="Read Selection")
        self._selection_getter = getter
        self._read_btn.clicked.connect(self._get_selection)
        if getter is None:
            self._read_btn.enabled = False
        super().__init__(
            value=value,
            bind=bind,
            widgets=[self._label_0, self._line_edit, self._label_1, self._read_btn],
            layout="horizontal",
            labels=False,
            **kwargs,
        )
        self.margins = (0, 0, 0, 0)

    def _get_selection(self):
        self.set_value(self._selection_getter(self))

    def get_value(self) -> SelectionType | None:
        text = self._line_edit.value.strip()
        if text == "":
            return None
        if not SLICE_PATTERN.match(text):
            raise ValueError(f"Cannot interpret {text} as slices")
        rsl_str, csl_str = text.split(",")
        r0, r1 = rsl_str.split(":")
        c0, c1 = csl_str.split(":")
        return (
            (_str_to_index(r0), _str_to_index(r1)),
            (_str_to_index(c0), _str_to_index(c1)),
        )

    def set_value(self, value: SelectionType | None):
        if value is None:
            self._line_edit.value = ""
        else:
            rsl, csl = value
            r0, r1 = rsl
            c0, c1 = csl
            r0 = _index_to_str(r0)
            r1 = _index_to_str(r1)
            c0 = _index_to_str(c0)
            c1 = _index_to_str(c1)
            self._line_edit.value = f"{r0}:{r1}, {c0}:{c1}"


def _index_to_str(s: int | None) -> str:
    return "" if s is None else s


def _str_to_index(s: str) -> int | None:
    s0 = s.strip()
    if s0 == "":
        return None
    return int(s0)
