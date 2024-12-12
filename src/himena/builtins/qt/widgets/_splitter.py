from __future__ import annotations
from typing import Literal

from qtpy import QtWidgets as QtW, QtCore, QtGui


class QSplitterHandle(QtW.QSplitterHandle):
    def __init__(self, parent: QtW.QSplitter, side: Literal["left", "right"] = "right"):
        super().__init__(QtCore.Qt.Orientation.Horizontal, parent)
        parent.setHandleWidth(8)
        self._sizes = [320, 80]
        self.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self._pos_press = QtCore.QPoint()
        # (symbol when closed, symbol when open)
        if side == "left":
            self._symbols = (">", "<")
            self._my_index = 0
        else:
            self._symbols = ("<", ">")
            self._my_index = -1

    def is_closed(self) -> bool:
        return self.splitter().sizes()[self._my_index] == 0

    def paintEvent(self, a0):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        pen = QtGui.QPen(QtCore.Qt.GlobalColor.gray, 1.5)
        painter.setPen(pen)
        painter.setBrush(QtCore.Qt.GlobalColor.gray)
        font = painter.font()
        font.setBold(True)
        painter.setFont(font)

        width = self.width()
        height = self.height()
        if self.is_closed():
            text = self._symbols[0]
        else:
            text = self._symbols[1]
        painter.drawLine(width // 2, 3, width // 2, height // 2 - 9)
        painter.drawText(width // 2 - 2, height // 2 + 5, text)
        painter.drawLine(width // 2, height // 2 + 9, width // 2, height - 3)

    def mousePressEvent(self, a0: QtGui.QMouseEvent) -> None:
        """Collapse/expand side area."""
        self._pos_press = a0.pos()
        return super().mousePressEvent(a0)

    def mouseReleaseEvent(self, a0):
        if (a0.pos() - self._pos_press).manhattanLength() < 2:
            self.toggle()
        return super().mouseReleaseEvent(a0)

    def toggle(self):
        parent = self.splitter()
        sizes = parent.sizes()
        if self.is_closed():
            parent.setSizes(self._sizes)
        else:
            self._sizes = sizes
            sizes = [1, 1]
            sizes[self._my_index] = 0
            parent.setSizes(sizes)
        return
