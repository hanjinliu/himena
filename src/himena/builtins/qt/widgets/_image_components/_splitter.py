from __future__ import annotations

from qtpy import QtWidgets as QtW, QtCore, QtGui


class QImageViewSplitterHandle(QtW.QSplitterHandle):
    def __init__(self, o, parent):
        super().__init__(o, parent)
        self._sizes = [320, 80]
        self.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)

    def is_closed(self) -> bool:
        return self.splitter().sizes()[1] == 0

    def paintEvent(self, a0):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        pen = QtGui.QPen(QtCore.Qt.GlobalColor.gray, 1)
        painter.setPen(pen)
        painter.setBrush(QtCore.Qt.GlobalColor.gray)

        width = self.width()
        height = self.height()
        text = "<" if self.is_closed() else ">"  # text to display
        painter.drawLine(width // 2, 3, width // 2, height // 2 - 9)
        painter.drawText(width // 2 - 2, height // 2 + 5, text)
        painter.drawLine(width // 2, height // 2 + 9, width // 2, height - 3)

    def mousePressEvent(self, a0: QtGui.QMouseEvent) -> None:
        """Collapse/expand side area."""
        self.toggle()
        return super().mousePressEvent(a0)

    def toggle(self):
        parent = self.splitter()
        sizes = parent.sizes()
        if self.is_closed():
            parent.setSizes(self._sizes)
        else:
            self._sizes = sizes
            parent.setSizes([1, 0])
        return
