from __future__ import annotations

from typing import TYPE_CHECKING, Any
from qtpy import QtCore, QtWidgets as QtW, QtGui
from himena.qt._qtitlebar import QTitleBarToolButton, QWidgetTitleBar
from himena.types import Size
from himena.plugins import _checker

if TYPE_CHECKING:
    from himena.widgets._wrapper import WidgetWrapper
    from himena.qt._qmain_window import QMainWindow


class QPopupView(QtW.QFrame):
    def __init__(self, parent: QMainWindow):
        # NOTE: Don't use Popup window type. Command palette is also using the default
        # window type. Also, Popup window is not compatible with the rounded corners in
        # some platforms.
        super().__init__(parent)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)

        # Add shadow effect
        shadow = QtW.QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setXOffset(0)
        shadow.setYOffset(5)
        shadow.setColor(QtGui.QColor(0, 0, 0, 100))
        self.setGraphicsEffect(shadow)

        self._titlebar = QWidgetTitleBar()
        self._titlebar.set_font_size(12)
        self._titlebar.set_selectable()
        self._close_btn = QTitleBarToolButton("✕")
        self._close_btn.clicked.connect(self.close)
        self._titlebar.add_button(self._close_btn)
        self._container = QtW.QWidget()
        self._inner_layout = QtW.QVBoxLayout(self._container)
        layout = QtW.QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.addWidget(self._titlebar)
        layout.addWidget(self._container)

        self._main_window = parent
        self._win: WidgetWrapper | None = None
        self._interf: Any | None = None

    def set_title(self, title: str):
        self._titlebar.setTitle(title)

    def popup_widget(
        self,
        widget: QtW.QWidget,
        interf: Any | None = None,
        win: WidgetWrapper[QtW.QWidget] | None = None,
    ):
        self._inner_layout.addWidget(widget)
        self.adjustSize()
        self.show()
        _checker.call_widget_added_callback(interf)
        margin = 50
        qsize = self._main_window.size() - QtCore.QSize(margin * 2, margin * 2)
        size_old = Size(self.width(), self.height() - 18)
        size_new = Size(qsize.width(), qsize.height() - 18)
        self.resize(qsize)
        self.move(QtCore.QPoint(margin, margin))
        if interf is None:
            interf = widget
        _checker.call_widget_resized_callback(interf, size_old, size_new)
        self._win = win
        self._interf = interf
        widget.setFocus()

    def closeEvent(self, a0):
        if self._win is None:
            return super().closeEvent(a0)
        _checker.call_widget_closed_callback(self._interf)
        if hasattr(self._interf, "to_model"):
            # update the original widget
            model = self._interf.to_model()  # type: ignore
            self._win.update_model(model)
        super().closeEvent(a0)
        self._main_window._move_focus_to(self._win.widget)

    def keyPressEvent(self, a0):
        if a0.key() == QtCore.Qt.Key.Key_Escape:
            self.close()
        return super().keyPressEvent(a0)
