from __future__ import annotations

from qtpy import QtWidgets as QtW, QtCore
from qtpy.QtCore import Qt, Signal
from himena.types import DockArea, DockAreaString


class QDockWidget(QtW.QDockWidget):
    closed = QtCore.Signal()
    whats_this = QtCore.Signal()

    def __init__(
        self,
        widget: QtW.QWidget,
        title: str,
        allowed_areas: list[DockAreaString | DockArea] | None = None,
    ):
        super().__init__(title)
        self.setWidget(widget)
        _titlebar = QDockWidgetTitleBar(title, self)
        self.setTitleBarWidget(_titlebar)
        _titlebar.closeSignal.connect(self.close)
        _titlebar.whatsThisSignal.connect(self.whats_this.emit)
        if allowed_areas is None:
            allowed_areas = [
                DockArea.LEFT,
                DockArea.RIGHT,
                DockArea.TOP,
                DockArea.BOTTOM,
            ]
        else:
            allowed_areas = [DockArea(area) for area in allowed_areas]
        areas = QtCore.Qt.DockWidgetArea.NoDockWidgetArea
        for allowed_area in allowed_areas:
            areas |= _DOCK_AREA_MAP[allowed_area]
        self.setAllowedAreas(areas)
        self._is_closing = False

    @staticmethod
    def area_normed(area) -> QtCore.Qt.DockWidgetArea:
        if area is not None:
            area = DockArea(area)
        return _DOCK_AREA_MAP[area]

    def showEvent(self, a0):
        super().showEvent(a0)
        self._is_closing = False

    def closeEvent(self, event):
        self._is_closing = True
        self.closed.emit()
        super().closeEvent(event)

    def isVisible(self) -> bool:
        if self._is_closing:
            return False
        return super().isVisible()


_DOCK_AREA_MAP = {
    DockArea.TOP: QtCore.Qt.DockWidgetArea.TopDockWidgetArea,
    DockArea.BOTTOM: QtCore.Qt.DockWidgetArea.BottomDockWidgetArea,
    DockArea.LEFT: QtCore.Qt.DockWidgetArea.LeftDockWidgetArea,
    DockArea.RIGHT: QtCore.Qt.DockWidgetArea.RightDockWidgetArea,
    None: QtCore.Qt.DockWidgetArea.NoDockWidgetArea,
}


class QDockWidgetTitleFrame(QtW.QFrame):
    """The title bar horizontal line."""

    def __init__(self):
        super().__init__()
        self.setFrameShape(QtW.QFrame.Shape.HLine)
        self.setFrameShadow(QtW.QFrame.Shadow.Sunken)
        self.setSizePolicy(
            QtW.QSizePolicy.Policy.Expanding, QtW.QSizePolicy.Policy.Fixed
        )


class QDockToolButton(QtW.QToolButton):
    def __init__(self, text: str) -> None:
        super().__init__()
        self.setText(text)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(QtCore.QSize(16, 16))


class QDockWidgetTitleBar(QtW.QWidget):
    """A custom title bar for a dock widget"""

    whatsThisSignal = Signal()
    closeSignal = Signal()

    def __init__(self, title: str = "", parent: QtW.QWidget | None = None) -> None:
        super().__init__(parent)
        _layout = QtW.QHBoxLayout(self)
        _layout.setContentsMargins(4, 0, 4, 0)
        _layout.setSpacing(0)

        self._title_label = QtW.QLabel()
        self._title_label.setContentsMargins(0, 0, 0, 0)

        _frame = QDockWidgetTitleFrame()
        self._close_button = QDockToolButton("✕")
        self._close_button.setToolTip("Close the widget.")

        self._whats_this_button = QDockToolButton("?")
        self._whats_this_button.setToolTip("What's this widget?")

        _layout.addWidget(self._title_label)
        _layout.addWidget(_frame)
        _layout.addWidget(self._whats_this_button)
        _layout.addWidget(self._close_button)
        _layout.setAlignment(self._close_button, Qt.AlignmentFlag.AlignRight)

        self._whats_this_button.clicked.connect(self.whatsThisSignal.emit)
        self._close_button.clicked.connect(self.close_button_clicked)

        self.setTitle(title)
        self.setFixedHeight(16)
        self.setCursor(Qt.CursorShape.OpenHandCursor)

    def close_button_clicked(self):
        self.closeSignal.emit()

    def title(self) -> str:
        """The title text."""
        return self._title_label.text()

    def setTitle(self, text: str):
        """Set the title text."""
        if text == "":
            self._title_label.setVisible(False)
        else:
            self._title_label.setVisible(True)
            self._title_label.setText(f"  {text}  ")

    def setBold(self, bold: bool):
        """Set the title text bold."""
        font = self._title_label.font()
        font.setBold(bold)
        self._title_label.setFont(font)
