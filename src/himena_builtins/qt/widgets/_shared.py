from __future__ import annotations
from qtpy import QtWidgets as QtW


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
