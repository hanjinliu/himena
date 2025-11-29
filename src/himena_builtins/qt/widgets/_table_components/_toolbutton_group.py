from qtpy import QtWidgets as QtW
from himena_builtins._consts import ICON_PATH
from himena.qt import QColoredToolButton


class QToolButtonGroup(QtW.QGroupBox):
    """A group of tool buttons with a horizontal layout."""

    def __init__(self, parent: QtW.QWidget | None = None):
        super().__init__(parent)
        self.setStyleSheet("QToolButtonGroup {margin: 0px;}")
        self.setLayout(QtW.QHBoxLayout(self))
        self.layout().setContentsMargins(0, 0, 0, 0)

        inner = QtW.QWidget()
        inner_layout = QtW.QHBoxLayout(inner)
        self.setContentsMargins(0, 0, 0, 0)
        inner_layout.setContentsMargins(0, 0, 0, 0)
        inner_layout.setSpacing(1)
        self._inner_layout = inner_layout
        self.layout().addWidget(inner)

    def add_tool_button(self, callback, icon: str) -> QColoredToolButton:
        """Create a tool button with the given icon and callback."""
        btn = QColoredToolButton(callback, ICON_PATH / f"{icon}.svg")
        self._inner_layout.addWidget(btn)
        return btn
