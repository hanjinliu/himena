from __future__ import annotations
from qtpy import QtWidgets as QtW


def labeled(text: str, widget: QtW.QWidget, *more_widgets: QtW.QWidget) -> QtW.QWidget:
    new = QtW.QWidget()
    layout = QtW.QHBoxLayout(new)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.addWidget(QtW.QLabel(text))
    layout.addWidget(widget)
    for w in more_widgets:
        layout.addWidget(w)
    return new
