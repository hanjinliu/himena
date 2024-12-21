from __future__ import annotations
from concurrent.futures import Future
from typing import TYPE_CHECKING
from enum import Enum
from qtpy import QtWidgets as QtW, QtCore, QtGui
from qtpy.QtCore import Qt

from himena.qt._qprogress import QCircularProgressBar, QLabeledCircularProgressBar

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
        if widget := parent.widget_area(0):
            return widget.rect()
        return QtCore.QRect()

    def alignTopLeft(self, offset=(3, 3)):
        pos = self.viewRect().topLeft()
        pos.setX(pos.x() + offset[0])
        pos.setY(pos.y() + offset[1])
        self.move(pos)

    def alignTopRight(self, offset=(3, 3)):
        pos = self.viewRect().topRight()
        pos.setX(pos.x() - self.rect().width() - offset[0])
        pos.setY(pos.y() + offset[1])
        self.move(pos)

    def alignBottomLeft(self, offset=(3, 3)):
        pos = self.viewRect().bottomLeft()
        pos.setX(pos.x() + offset[0])
        pos.setY(pos.y() - self.rect().height() - offset[1])
        self.move(pos)

    def alignBottomRight(self, offset=(3, 3)):
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
        self._close_btn = QtW.QPushButton("✕")
        self._close_btn.setFixedSize(15, 15)
        self._close_btn.setParent(
            self, self._close_btn.windowFlags() | Qt.WindowType.FramelessWindowHint
        )
        self._close_btn.clicked.connect(self._hide)

    def hideLater(self, sec: float = 5):
        """Hide overlay widget after a delay."""
        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(int(sec * 1000))
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._hide)
        self._timer.start()
        return None

    def _hide(self):
        self._close_btn.hide()
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
        self._close_btn.hide()
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
        self._close_btn.show()
        pos_loc = self.rect().topRight() - QtCore.QPoint(
            self._close_btn.width() + 5, -5
        )
        self._close_btn.move(self.mapToGlobal(pos_loc))
        return super().enterEvent(a0)

    def leaveEvent(self, a0: QtCore.QEvent) -> None:
        if self._timer is not None:
            self._timer.start()
        if not self.rect().contains(self.mapFromGlobal(QtGui.QCursor.pos())):
            self._close_btn.hide()
        return super().leaveEvent(a0)


class QJobStack(_QOverlayBase):
    job_finished = QtCore.Signal(QtW.QListWidgetItem)

    def __init__(self, parent: QTabWidget):
        super().__init__(parent)
        self._list_widget = QtW.QListWidget()
        self.addWidget(self._list_widget)
        self.setAnchor(Anchor.bottom_left)
        self.job_finished.connect(self._on_job_finished)

    def add_future(self, future: Future, desc: str, total: int = 0):
        pbar = QCircularProgressBar()
        pbar.setButtonState("square")
        pbar.setValue(-1)

        @pbar.abortRequested.connect
        def _aborting():
            pass  # TODO: not working yet

        item = QtW.QListWidgetItem()
        labeled_pbar = QLabeledCircularProgressBar(desc, pbar)

        future.add_done_callback(lambda _: self.job_finished.emit(item))
        self._add_item_for_future(item, labeled_pbar)

    def _add_item_for_future(self, item: QtW.QListWidgetItem, widget: QtW.QWidget):
        lw = self._list_widget
        lw.addItem(item)
        lw.setIndexWidget(lw.model().index(lw.count() - 1, 0), widget)
        self.adjustHeight()
        self.show()

    def _on_job_finished(self, item: QtW.QListWidgetItem):
        lw = self._list_widget
        lw.takeItem(lw.row(item))
        if lw.count() == 0:
            self.hide()
        else:
            self.adjustHeight()

    def adjustHeight(self):
        height = min(20 * min(2, self._list_widget.count()) + 6, 200)
        self._list_widget.setFixedHeight(height)
        self.setFixedHeight(height + 4)
        self.alignToParent()


class QWhatsThisWidget(_QOverlayBase):
    def __init__(self, parent: QTabWidget):
        super().__init__(parent)
        self._close_btn = QtW.QPushButton("✕")
        self._close_btn.setFixedSize(15, 15)
        self._close_btn.setParent(
            self, self._close_btn.windowFlags() | Qt.WindowType.FramelessWindowHint
        )
        self._close_btn.clicked.connect(self._hide)
        self.setAnchor(Anchor.top_right)

    def _hide(self):
        self._close_btn.hide()
        self.hide()
        return None

    def set_text(self, text: str, style: str = "plain"):
        text_widget = QtW.QTextEdit()
        text_widget.setFont(QtGui.QFont("Arial", 10))
        if style == "plain":
            text_widget.setText(text)
        elif style == "markdown":
            text_widget.setMarkdown(text)
        elif style == "html":
            text_widget.setHtml(text)
        else:
            raise ValueError(f"Unknown style: {style}")
        self.addWidget(text_widget)

    def enterEvent(self, a0: QtCore.QEvent) -> None:
        self._close_btn.show()
        pos_loc = self.rect().topRight() - QtCore.QPoint(
            self._close_btn.width() + 5, -5
        )
        self._close_btn.move(self.mapToGlobal(pos_loc))
        return super().enterEvent(a0)

    def leaveEvent(self, a0: QtCore.QEvent) -> None:
        if not self.rect().contains(self.mapFromGlobal(QtGui.QCursor.pos())):
            self._close_btn.hide()
        return super().leaveEvent(a0)
