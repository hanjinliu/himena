from __future__ import annotations
from qtpy import QtWidgets as QtW, QtCore


class QWidgetTitleBarFrame(QtW.QFrame):
    """The title bar horizontal line."""

    def __init__(self):
        super().__init__()
        self.setFrameShadow(QtW.QFrame.Shadow.Sunken)
        self.setSizePolicy(
            QtW.QSizePolicy.Policy.Expanding, QtW.QSizePolicy.Policy.Fixed
        )


class QTitleBarToolButton(QtW.QToolButton):
    def __init__(self, text: str) -> None:
        super().__init__()
        self.setText(text)
        self.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(QtCore.QSize(16, 16))


class QWidgetTitleBar(QtW.QWidget):
    """A custom title bar."""

    def __init__(self, title: str = "", parent: QtW.QWidget | None = None) -> None:
        super().__init__(parent)
        self._indent = 2
        self._layout = _layout = QtW.QHBoxLayout(self)
        _layout.setContentsMargins(4, 0, 4, 0)
        _layout.setSpacing(0)

        self._title_label = QtW.QLabel()
        self._title_label.setObjectName("TitleBarTitleLabel")
        self._title_label.setContentsMargins(0, 0, 0, 0)

        self._frame = QWidgetTitleBarFrame()
        _layout.addWidget(self._title_label)
        _layout.addWidget(self._frame)

        self.setTitle(title)
        self.setFixedHeight(16)

    def set_font_size(self, size: int):
        """Set the font size of the title."""
        font = self._title_label.font()
        font.setPointSize(size)
        self._title_label.setFont(font)

    def add_button(self, btn: QTitleBarToolButton):
        self._layout.addWidget(btn)
        self._layout.setAlignment(btn, QtCore.Qt.AlignmentFlag.AlignRight)

    def add_sizegrip(self):
        """Add size grip to the top-left corner"""
        size_grip = QtW.QSizeGrip(self)
        size_grip.setFixedWidth(8)
        self._layout.insertWidget(
            0,
            size_grip,
            0,
            QtCore.Qt.AlignmentFlag.AlignTop | QtCore.Qt.AlignmentFlag.AlignLeft,
        )
        self._indent = 0

    def frameWidget(self) -> QWidgetTitleBarFrame:
        """Get the frame widget."""
        return self._frame

    def title(self) -> str:
        """The title text."""
        return self._title_label.text()

    def setTitle(self, text: str):
        """Set the title text."""
        if text == "":
            self._title_label.setVisible(False)
        else:
            self._title_label.setVisible(True)
            ind = " " * self._indent
            self._title_label.setText(f"{ind}{text}  ")
