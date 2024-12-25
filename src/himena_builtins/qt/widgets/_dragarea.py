from qtpy import QtWidgets as QtW, QtCore, QtGui
from superqt import QIconifyIcon


class QDraggableArea(QtW.QWidget):
    """A draggable area implemented with dragged event."""

    dragged = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        icon = QIconifyIcon("qlementine-icons:drag-16", color="#777777")
        self._icon = icon
        self._pixmap = icon.pixmap(100, 100)

        self.setCursor(QtCore.Qt.CursorShape.SizeAllCursor)
        self._pressed = False
        self.setToolTip("Drag area")
        self.setMinimumWidth(15)

    def paintEvent(self, a0):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.SmoothPixmapTransform)
        target_rect = self.rect()
        painter.drawPixmap(target_rect, self._pixmap)

    def mousePressEvent(self, a0):
        if a0.button() == QtCore.Qt.MouseButton.LeftButton:
            self._pressed = True

    def mouseMoveEvent(self, a0):
        if self._pressed:
            self._pressed = False
            self.dragged.emit()

    def mouseReleaseEvent(self, a0):
        self._pressed = False
