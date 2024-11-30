from __future__ import annotations

from qtpy import QtWidgets as QtW, QtGui


class QInstruction(QtW.QLabel):
    def __init__(self, text: str):
        super().__init__(text)
        self.setFont(QtGui.QFont("Arial", 11))
