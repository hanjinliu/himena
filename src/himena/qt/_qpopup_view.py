from __future__ import annotations

from typing import TYPE_CHECKING, Any
from qtpy import QtCore, QtWidgets as QtW, QtGui
from himena.qt._utils import split_widget_and_interface
from himena.qt._qtitlebar import QTitleBarToolButton, QWidgetTitleBar
from himena.types import WidgetDataModel

if TYPE_CHECKING:
    from himena.widgets._wrapper import WidgetWrapper
    from himena.qt._qmain_window import QMainWindow


class QPopupView(QtW.QFrame):
    def __init__(self, parent: QMainWindow, win: WidgetWrapper | None = None):
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
        self._win = win
        self._interf: Any | None = None

    def popup_data_model(self, model: WidgetDataModel):
        interf = self._main_window._himena_main_window._pick_widget(model)
        self._interf = interf
        _, qwidget = split_widget_and_interface(interf)

        self._inner_layout.addWidget(qwidget)
        self._titlebar.set_font_size(12)
        self._titlebar.setTitle(model.title)
        self.adjustSize()
        self.show()
        margin = 50
        size = self._main_window.size() - QtCore.QSize(margin * 2, margin * 2)
        self.resize(size)
        self.move(QtCore.QPoint(margin, margin))
        qwidget.setFocus()

    def closeEvent(self, a0):
        if self._win is None:
            return super().closeEvent(a0)
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
