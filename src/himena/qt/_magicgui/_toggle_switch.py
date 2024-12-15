from __future__ import annotations

from qtpy import QtWidgets as QtW, QtCore, QtGui
from qtpy.QtCore import Qt, Signal, Property

from magicgui.widgets.bases import ButtonWidget
from magicgui.backends._qtpy.widgets import QBaseButtonWidget


class QToggleSwitch(QtW.QWidget):
    """
    A iPhone style toggle switch.
    See https://stackoverflow.com/questions/14780517/toggle-switch-in-qt

     ooooo
    ooooooo:::::
    ooooooo:::::
     ooooo

    Properties
    ----------
    - onColor: QtGui.QColor
    - offColor: QtGui.QColor
    - handleColor: QtGui.QColor
    """

    toggled = Signal(bool)

    def __init__(self, parent: QtW.QWidget | None = None):
        super().__init__(parent)
        self.setSizePolicy(
            QtW.QSizePolicy.Policy.Minimum, QtW.QSizePolicy.Policy.Expanding
        )
        self._on_color = QtGui.QColor("#4D79C7")
        self._off_color = QtGui.QColor("#909090")
        self._handle_color = QtGui.QColor("#d5d5d5")
        self._margin = 2
        self._checked = False
        self.setSize(12)
        self.toggled.connect(self._set_checked)
        self._anim = QtCore.QPropertyAnimation(self, b"offset", self)

    def setSize(self, size: int):
        self._height = size
        self.offset = size
        self.setFixedSize(
            (self._height + self._margin) * 2, self._height + self._margin * 2
        )

    @Property(QtGui.QColor)
    def onColor(self):
        return self._on_color

    @onColor.setter
    def onColor(self, brsh: QtGui.QBrush):
        self._on_color = brsh

    @Property(QtGui.QColor)
    def offColor(self):
        return self._off_color

    @offColor.setter
    def offColor(self, brsh: QtGui.QBrush):
        self._off_color = brsh

    @Property(float)
    def offset(self):
        return self._x

    @offset.setter
    def offset(self, o: float):
        self._x = o
        self.update()

    @Property(QtGui.QColor)
    def handleColor(self):
        return self._handle_color

    @handleColor.setter
    def handleColor(self, color: QtGui.QColor):
        self._handle_color = color

    def sizeHint(self) -> QtCore.QSize:
        return QtCore.QSize(2 * (self._height + self._margin), self.minimumHeight())

    def minimumHeight(self) -> int:
        return self._height + 2 * self._margin

    def paintEvent(self, e):
        p = QtGui.QPainter(self)
        p.setPen(Qt.PenStyle.NoPen)
        _y = self._height / 2
        rrect = QtCore.QRect(
            self._margin,
            self._margin,
            self.width() - 2 * self._margin,
            self.height() - 2 * self._margin,
        )
        if self.isEnabled():
            p.setBrush(self._on_color if self._checked else self._off_color)
            p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
            p.setOpacity(0.8)
        else:
            p.setBrush(self._off_color)
            p.setOpacity(0.6)
        p.drawRoundedRect(rrect, _y, _y)
        p.setBrush(self._handle_color)
        p.setOpacity(1.0)
        p.drawEllipse(QtCore.QRectF(self.offset - _y, 0, self.height(), self.height()))

    def mouseReleaseEvent(self, e: QtGui.QMouseEvent):
        if e.button() & Qt.MouseButton.LeftButton:
            self.toggled.emit(not self.isChecked())
        return super().mouseReleaseEvent(e)

    def enterEvent(self, e):
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        return super().enterEvent(e)

    def toggle(self):
        return self.setChecked(not self.isChecked())

    def isChecked(self) -> bool:
        return self._checked

    def setChecked(self, val: bool):
        self._set_checked(val)
        self.toggled.emit(val)

    def _set_checked(self, val: bool):
        start = self.positionForValue(self._checked)
        end = self.positionForValue(val)

        # Do not re-animate if the value is the same
        if self._checked == val:
            return
        self._checked = val
        self._anim.setStartValue(start)
        self._anim.setEndValue(end)
        self._anim.setDuration(120)
        self._anim.start()

    def positionForValue(self, val: bool) -> int:
        if val:
            return int(self.width() - self._height)
        else:
            return self._height // 2


class _QLabel(QtW.QLabel):
    clicked = Signal()

    def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
        if ev.button() & Qt.MouseButton.LeftButton:
            self.clicked.emit()
        return None


class QLabeledToggleSwitch(QtW.QWidget):
    def __init__(self, parent: QtW.QWidget | None = None):
        super().__init__(parent)
        layout = QtW.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._switch = QToggleSwitch(self)
        self._text = _QLabel(self)
        self._text.clicked.connect(self._switch.toggle)
        layout.addWidget(self._switch)
        layout.addWidget(self._text)
        self.setLayout(layout)

    @property
    def toggled(self):
        # NOTE: This method is mandatory for the magicgui backend to work.
        return self._switch.toggled

    def setSize(self, size: int):
        self._switch.setSize(size)

    def isChecked(self) -> bool:
        return self._switch.isChecked()

    def setChecked(self, val: bool):
        self._switch.setChecked(val)

    def enterEvent(self, e):
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        return super().enterEvent(e)

    def isDown(self) -> bool:
        return self.isChecked()

    def setDown(self, a0: bool) -> None:
        return self.setChecked(a0)

    def text(self) -> str:
        return self._text.text()

    def setText(self, text: str):
        self._text.setText(text)

    def click(self):
        self.toggle()

    def toggle(self):
        self.setChecked(not self.isChecked())

    def minimumHeight(self) -> int:
        return self._switch.minimumHeight()

    def sizeHint(self) -> QtCore.QSize:
        switch_hint = self._switch.sizeHint()
        text_hint = self._text.sizeHint()
        return QtCore.QSize(
            switch_hint.width() + text_hint.width(),
            max(switch_hint.height(), text_hint.height()),
        )


class ToggleSwitch(ButtonWidget):
    """A toggle switch widget behaves like a check box."""

    def __init__(self, **kwargs):
        super().__init__(
            widget_type=QBaseButtonWidget,
            backend_kwargs={"qwidg": QLabeledToggleSwitch},
            **kwargs,
        )
        self.native: QLabeledToggleSwitch
