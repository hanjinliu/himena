from __future__ import annotations

from qtpy import QtCore, QtWidgets as QtW, QtGui
from himena.utils.enum import StrEnum


class ToolTipBehavior(StrEnum):
    """Tooltip behavior when the parent window loses focus."""

    STAY = "stay"  # Stay in place
    FOLLOW = "follow"  # Follow the cursor
    UNTIL_MOVE = "until_move"  # Stay until the cursor moves


class QToolTipWidget(QtW.QLabel):
    def __init__(self, parent: QtW.QWidget | None = None):
        super().__init__(parent, QtCore.Qt.WindowType.ToolTip)
        self.setObjectName("HimenaToolTip")
        self.setWindowFlag(QtCore.Qt.WindowType.FramelessWindowHint)
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        self.hide()
        self._timer = QtCore.QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.hide)
        self._offset = QtCore.QPoint(14, 18)
        self._behavior = ToolTipBehavior.FOLLOW

    def set_behavior(self, behavior: str) -> None:
        self._behavior = ToolTipBehavior(behavior)

    def show_tooltip(self, text: str, duration: float = 3.0) -> None:
        """Show tooltip next to the cursor for a duration (sec)."""
        self._timer.stop()
        if not text:
            self.setText(text)
            self.hide()
        else:
            self.setText(text)
            self.adjustSize()
            self.move_tooltip(QtGui.QCursor.pos())
            self.show()
            self.raise_()
            self._timer.start(int(duration * 1000))

    def move_tooltip(self, pos: QtCore.QPoint) -> None:
        self.move(pos + self._offset)
