from __future__ import annotations
from qtpy import QtWidgets as QtW
import numpy as np
from numpy.typing import NDArray


def labeled(
    text: str,
    widget: QtW.QWidget,
    *more_widgets: QtW.QWidget,
    label_width: int | None = None,
) -> QtW.QWidget:
    new = QtW.QWidget()
    layout = QtW.QHBoxLayout(new)
    layout.setContentsMargins(0, 0, 0, 0)
    label = QtW.QLabel(text)
    layout.addWidget(label)
    layout.addWidget(widget)
    for w in more_widgets:
        layout.addWidget(w)
    if label_width:
        label.setFixedWidth(label_width)
    return new


def quick_min_max(
    arr: NDArray[np.number],
    down_sample_to: int = 1048576,
) -> tuple[float, float]:
    if arr.dtype.kind == "b":
        return (0.0, 1.0)
    down_sample_factor = arr.size / down_sample_to
    if down_sample_factor <= 1.0:
        return arr.min(), arr.max()
    stride = int(np.ceil(down_sample_factor))
    arr_ref = arr[::stride]
    return arr_ref.min(), arr_ref.max()


def spacer_widget() -> QtW.QWidget:
    empty = QtW.QWidget()
    empty.setSizePolicy(
        QtW.QSizePolicy.Policy.Expanding, QtW.QSizePolicy.Policy.Preferred
    )
    return empty


def index_contains(c: int | slice | np.ndarray, idx: int) -> bool:
    if isinstance(c, slice):
        return c.start <= idx < c.stop
    elif isinstance(c, np.ndarray):
        return idx in c
    else:
        return c == idx
