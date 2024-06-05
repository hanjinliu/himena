from __future__ import annotations

from qtpy import QtWidgets as QtW, QtCore, QtGui


class QRenameLineEdit(QtW.QLineEdit):
    rename_requested = QtCore.Signal(str)

    def __init__(self, parent: QtW.QWidget):
        super().__init__(parent)
        self.setHidden(True)

        @self.editingFinished.connect
        def _():
            if not self.isVisible():
                return
            self.setHidden(True)
            text = self.text()
            if text:
                self.rename_requested.emit(text)

    def keyPressEvent(self, a0: QtGui.QKeyEvent) -> None:
        if a0.key() == QtCore.Qt.Key.Key_Escape:
            self.setHidden(True)
        return super().keyPressEvent(a0)
