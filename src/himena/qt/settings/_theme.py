from __future__ import annotations
from functools import partial
from typing import TYPE_CHECKING
from qtpy import QtWidgets as QtW, QtGui, QtCore
from qtpy.QtCore import Qt, Signal

from himena.consts import DefaultFontFamily
from himena.style import Theme, get_global_styles

if TYPE_CHECKING:
    from himena.widgets import MainWindow


class QThemePanel(QtW.QWidget):
    def __init__(self, ui: MainWindow) -> None:
        super().__init__()
        self._ui = ui
        self._labels: dict[str, QThemeSelectionLabel] = {}
        _layout = QtW.QGridLayout()
        row = 0
        col = 0
        ncols = 6

        for name, theme in get_global_styles().items():
            label = QThemeSelectionLabel(theme)
            label.setToolTip(name)
            self._labels[name] = label
            label.clicked.connect(partial(self.setTheme, name=name))
            _layout.addWidget(label, row, col)
            col += 1
            if col >= ncols:
                row += 1
                col = 0

        self.setLayout(_layout)
        self.setMinimumSize(200, 100)
        self._update_check_state(ui.theme.name)

    def setTheme(self, name: str):
        """Set the theme of the application and update the main window."""
        prof = self._ui.app_profile
        prof.theme = name
        prof.save()
        self._update_check_state(name)
        self._ui.theme = name

    def _update_check_state(self, name: str):
        for key, wdt in self._labels.items():
            wdt.setChecked(key == name)


class QThemeSelectionLabel(QtW.QLabel):
    clicked = Signal()

    def __init__(self, theme: Theme) -> None:
        super().__init__()
        self._theme = theme
        self.setFixedSize(30, 30)
        self.setFont(QtGui.QFont(DefaultFontFamily, 16))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._checked = False

    def setChecked(self, checked: bool):
        self._checked = checked
        self.update()

    def mouseReleaseEvent(self, ev: QtGui.QMouseEvent) -> None:
        self.clicked.emit()
        return super().mouseReleaseEvent(ev)

    def sizeHint(self) -> QtCore.QSize:
        return QtCore.QSize(30, 30)

    def paintEvent(self, a0: QtGui.QPaintEvent) -> None:
        painter = QtGui.QPainter(self)
        geo = self.rect()

        grad = QtGui.QLinearGradient(
            QtCore.QPointF(geo.topLeft()), QtCore.QPointF(geo.bottomRight())
        )
        grad.setColorAt(0, QtGui.QColor(self._theme.background_dim))
        grad.setColorAt(1, QtGui.QColor(self._theme.background_strong))
        path = QtGui.QPainterPath(QtCore.QPointF(geo.topLeft()))
        path.lineTo(QtCore.QPointF(geo.topRight()))
        path.lineTo(QtCore.QPointF(geo.bottomLeft()))
        painter.fillPath(path, grad)

        grad = QtGui.QLinearGradient(
            QtCore.QPointF(geo.topLeft()), QtCore.QPointF(geo.bottomRight())
        )
        grad.setColorAt(0, QtGui.QColor(self._theme.highlight_dim))
        grad.setColorAt(1, QtGui.QColor(self._theme.highlight_strong))
        path = QtGui.QPainterPath(QtCore.QPointF(geo.topRight()))
        path.lineTo(QtCore.QPointF(geo.bottomLeft()))
        path.lineTo(QtCore.QPointF(geo.bottomRight()))
        painter.fillPath(path, grad)

        if self._checked:
            painter.setPen(QtGui.QPen(QtGui.QColor(255, 20, 20), 3))
            painter.drawRect(geo)

        painter.setPen(QtGui.QPen(QtGui.QColor(self._theme.foreground), 3))
        painter.drawText(geo, Qt.AlignmentFlag.AlignCenter, "A")
        return None
