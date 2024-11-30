from __future__ import annotations
from typing import TYPE_CHECKING
from enum import Enum
from qtpy import QtWidgets as QtW, QtCore
from qtpy.QtCore import Qt

if TYPE_CHECKING:
    from himena.qt._qtab_widget import QTabWidget


class Anchor(Enum):
    """Anchor position"""

    top_left = "top_left"
    top_right = "top_right"
    bottom_left = "bottom_left"
    bottom_right = "bottom_right"


class _QOverlayBase(QtW.QDialog):
    """Overlay widget appears at the fixed position."""

    def __init__(self, parent: QTabWidget):
        super().__init__(parent, Qt.WindowType.SubWindow)
        self._widget = None

        _layout = QtW.QVBoxLayout()
        _layout.setContentsMargins(2, 2, 2, 2)
        _layout.setSpacing(0)

        self.setLayout(_layout)

        parent.resized.connect(self.alignToParent)
        self.setAnchor(Anchor.bottom_right)
        self.setVisible(False)

    def addWidget(self, widget: QtW.QWidget):
        """Set the central widget."""
        if self._widget is not None:
            self.removeWidget()
        self.layout().addWidget(widget)
        self.resize(widget.sizeHint())
        self._widget = widget
        self.alignToParent()

    def removeWidget(self):
        """Remove the central widget."""
        self._widget.setParent(None)
        self._widget = None
        self.resize(QtCore.QSize(0, 0))

    def widget(self) -> QtW.QWidget:
        """The central widget."""
        return self._widget

    def anchor(self) -> Anchor:
        """Anchor position."""
        return self._anchor

    def setAnchor(self, anc: Anchor | str) -> None:
        """Set anchor position of the overlay widget."""
        self._anchor = Anchor(anc)
        return self.alignToParent()

    def show(self):
        """Show the overlay widget with animation."""
        super().show()
        self.alignToParent()
        return None

    def alignToParent(self):
        """Position widget at the bottom right edge of the parent."""
        if not self.isVisible():
            return
        qtable = self.parentWidget()
        # if not qtable or qtable.isEmpty():
        if not qtable:
            return
        if self._anchor == Anchor.bottom_left:
            self.alignBottomLeft()
        elif self._anchor == Anchor.bottom_right:
            self.alignBottomRight()
        elif self._anchor == Anchor.top_left:
            self.alignTopLeft()
        elif self._anchor == Anchor.top_right:
            self.alignTopRight()
        else:
            raise RuntimeError

    def viewRect(self) -> QtCore.QRect:
        """Return the parent table rect."""
        parent = self.parentWidget()
        if widget := parent.widget(0):
            return widget.rect()
        return QtCore.QRect()

    def alignTopLeft(self, offset=(3, 3)):
        pos = self.viewRect().topLeft()
        pos.setX(pos.x() + offset[0])
        pos.setY(pos.y() + offset[1])
        self.move(pos)

    def alignTopRight(self, offset=(21, 3)):
        pos = self.viewRect().topRight()
        pos.setX(pos.x() - self.rect().width() - offset[0])
        pos.setY(pos.y() + offset[1])
        self.move(pos)

    def alignBottomLeft(self, offset=(3, 3)):
        pos = self.viewRect().bottomLeft()
        pos.setX(pos.x() + offset[0])
        pos.setY(pos.y() - self.rect().height() - offset[1])
        self.move(pos)

    def alignBottomRight(self, offset=(21, 3)):
        pos = self.viewRect().bottomRight()
        pos.setX(pos.x() - self.rect().width() - offset[0])
        pos.setY(pos.y() - self.rect().height() - offset[1])
        self.move(pos)

    # fmt: off
    if TYPE_CHECKING:
        def parentWidget(self) -> QTabWidget: ...
    # fmt: on


class QNotificationWidget(_QOverlayBase):
    """The overlay widget appears at the fixed position."""

    def __init__(self, parent: QTabWidget, duration: int = 500):
        """
        The overlay widget appears at the fixed position.

        Parameters
        ----------
        parent : QTabWidget
            Parent table stack
        duration : int, default is 500
            Animation duration in msec.
        """
        super().__init__(parent)

        effect = QtW.QGraphicsOpacityEffect(self)
        effect.setOpacity(0.9)
        self.setGraphicsEffect(effect)
        self._effect = effect
        self.opacity_anim = QtCore.QPropertyAnimation(self._effect, b"opacity", self)
        self.geom_anim = QtCore.QPropertyAnimation(self, b"geometry", self)
        self._duration = duration
        self._timer: QtCore.QTimer | None = None

    def hideLater(self, sec: float = 5):
        """Hide overlay widget after a delay."""
        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(int(sec * 1000))
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._hide)
        self._timer.start()
        return None

    def _hide(self):
        if self.isVisible():
            self.setVisible(False)
            self._timer = None
        return None

    def slide_in(self):
        """Run animation that fades in the dialog with a slight slide up."""
        geom = self.geometry()
        self.geom_anim.setDuration(200)
        self.geom_anim.setStartValue(geom.translated(0, 20))
        self.geom_anim.setEndValue(geom)
        self.geom_anim.setEasingCurve(QtCore.QEasingCurve.Type.OutQuad)
        # fade in
        self.opacity_anim.setDuration(self._duration)
        self.opacity_anim.setStartValue(0)
        self.opacity_anim.setEndValue(0.9)
        self.geom_anim.start()
        self.opacity_anim.start()

    def show(self):
        """Show the overlay widget with animation."""
        super().show()
        self.slide_in()
        return None

    def hide(self) -> None:
        """Hide the overlay widget with animation."""
        self.opacity_anim.setDuration(self._duration)
        self.opacity_anim.setStartValue(0.9)
        self.opacity_anim.setEndValue(0)
        self.opacity_anim.start()

        @self.opacity_anim.finished.connect
        def _on_vanished():
            if self.isVisible():
                self.setVisible(False)
            self.opacity_anim.finished.disconnect()

        return None

    def show_and_hide_later(self, sec: float = 5):
        """Show the overlay widget with animation and hide after a delay."""
        self.show()
        self.hideLater(sec)
        return None

    def enterEvent(self, a0: QtCore.QEvent) -> None:
        if self._timer is not None:
            self._timer.stop()
        return super().enterEvent(a0)

    def leaveEvent(self, a0: QtCore.QEvent) -> None:
        if self._timer is not None:
            self._timer.start()
        return super().leaveEvent(a0)