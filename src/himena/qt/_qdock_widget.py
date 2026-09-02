from __future__ import annotations

from qtpy import QtWidgets as QtW, QtCore, QtGui
from qtpy.QtCore import Qt, Signal
from himena.types import DockArea, DockAreaString
from himena.qt._qtitlebar import QWidgetTitleBar


class QDockWidget(QtW.QDockWidget):
    """Custom dock widget used in the main window."""

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
        self._titlebar = QDockWidgetTitleBar(title, self)
        self.setTitleBarWidget(self._titlebar)
        self._titlebar.closeSignal.connect(self.close)
        self._titlebar.whatsThisSignal.connect(self.whats_this.emit)
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
        self._floating_flags_pending = False
        self._border_color = QtGui.QColor(128, 128, 128)
        self.topLevelChanged.connect(self._on_top_level_changed)

    @staticmethod
    def area_normed(area) -> QtCore.Qt.DockWidgetArea:
        if area is not None:
            area = DockArea(area)
        return _DOCK_AREA_MAP[area]

    def _on_top_level_changed(self, floating: bool) -> None:
        """Update the window type when the dock widget is floated/docked."""
        if floating:
            self._floating_flags_pending = True
            self._update_floating_window_flags()
        else:
            # Qt resets the window flags by itself when the widget is docked.
            self._floating_flags_pending = False

    def _update_floating_window_flags(self) -> None:
        """Make the floating dock widget a normal top-level window.

        Because this dock widget uses a custom title bar, Qt makes it a frameless
        `Qt.Tool` window when it is floated. Such a window is not always properly
        managed by the window manager (typically when the application is running
        over SSH X11 forwarding), in which case the floating widget does not
        receive any mouse/keyboard events. Turning it into a normal (frameless)
        window instead of a tool window avoids this problem.
        """
        if not self._floating_flags_pending:
            return
        if not self.isFloating():
            self._floating_flags_pending = False
            return
        if QtW.QApplication.mouseButtons() != Qt.MouseButton.NoButton:
            # The widget is being dragged. Changing the window flags now would
            # recreate the native window and break the dragging. Try later.
            QtCore.QTimer.singleShot(100, self._update_floating_window_flags)
            return
        self._floating_flags_pending = False
        if (self.windowFlags() & Qt.WindowType.WindowType_Mask) == Qt.WindowType.Window:
            return  # already a normal window
        was_visible = self.isVisible()
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
        if was_visible:
            self.show()  # setWindowFlags() hides the widget

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        # The dock widget may have just been dropped as a floating window.
        self._update_floating_window_flags()

    def paintEvent(self, a0):
        super().paintEvent(a0)
        if not self.isFloating():
            return
        # Qt does not paint the frame of a floating dock widget if it has a custom
        # title bar. Draw the border here, otherwise the floating widget does not
        # have any visible boundary.
        painter = QtGui.QPainter(self)
        painter.setPen(QtGui.QPen(self._border_color, 1))
        painter.drawRect(self.rect())

    def _get_border_color(self) -> QtGui.QColor:
        return self._border_color

    def _set_border_color(self, color) -> None:
        self._border_color = QtGui.QColor(color)
        self.update()

    # the border color of the floating window, to be set by the style sheet
    borderColor = QtCore.Property(QtGui.QColor, _get_border_color, _set_border_color)

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


class QDockWidgetTitleBar(QWidgetTitleBar):
    """A custom title bar for a dock widget"""

    whatsThisSignal = Signal()
    closeSignal = Signal()

    def __init__(self, title: str = "", parent: QtW.QWidget | None = None) -> None:
        super().__init__(title, parent)

        self.frameWidget().setFrameShape(QtW.QFrame.Shape.HLine)

        self._close_button = QDockToolButton("✕")
        self._close_button.setToolTip("Close the widget.")
        self._close_button.clicked.connect(self.close_button_clicked)

        self._whats_this_button = QDockToolButton("?")
        self._whats_this_button.setToolTip("What's this widget?")
        self._whats_this_button.clicked.connect(self.whatsThisSignal.emit)

        self.add_button(self._whats_this_button)
        self.add_button(self._close_button)

        self.setTitle(title)
        self.setFixedHeight(16)
        self.setCursor(Qt.CursorShape.OpenHandCursor)

    def close_button_clicked(self):
        self.closeSignal.emit()
