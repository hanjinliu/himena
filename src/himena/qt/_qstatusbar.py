from __future__ import annotations

from typing import TYPE_CHECKING
from qtpy import QtWidgets as QtW, QtCore

if TYPE_CHECKING:
    from himena.qt._qmain_window import QMainWindow


class QStatusBar(QtW.QStatusBar):
    def __init__(self, parent: QMainWindow):
        from himena import __version__

        super().__init__(parent)
        self._corner_widget = QtW.QWidget(self)
        layout = QtW.QHBoxLayout(self._corner_widget)
        layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        layout.setContentsMargins(4, 0, 4, 0)
        self._profile_btn = QtW.QPushButton(f"{parent._app.name}")
        self._profile_btn.setToolTip("Application profile")
        self._profile_btn.setObjectName("profileButton")
        self._profile_btn.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        layout.addWidget(self._profile_btn)
        version_label = QtW.QLabel(f"v{__version__}")
        version_label.setToolTip("Himena version")
        layout.addWidget(version_label)

        self.layout().setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        self.layout().addWidget(self._corner_widget)
