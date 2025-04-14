from __future__ import annotations

from typing import TYPE_CHECKING
from qtpy import QtWidgets as QtW, QtCore
from himena.profile import profile_dir

if TYPE_CHECKING:
    from himena.qt._qmain_window import QMainWindow


class QStatusBar(QtW.QStatusBar):
    def __init__(self, parent: QMainWindow):
        super().__init__(parent)
        self._corner_widget = QtW.QWidget(self)
        layout = QtW.QHBoxLayout(self._corner_widget)
        layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        layout.setContentsMargins(4, 0, 4, 0)
        self._profile_btn = QtW.QPushButton(f"{parent._app.name}")
        self._profile_btn.setToolTip("Application profile")
        self._profile_btn.setObjectName("profileButton")
        self._profile_btn.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self._profile_btn.clicked.connect(self._open_profile_info)
        layout.addWidget(self._profile_btn)

        self.layout().setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        self.layout().addWidget(self._corner_widget)

    def _open_profile_info(self) -> None:
        """Open the profile info."""
        info = QProfileInfo(self._profile_btn.text())
        info.setParent(self, QtCore.Qt.WindowType.Popup)
        info.show()
        info.move(
            self._profile_btn.mapToGlobal(QtCore.QPoint(0, 0))
            - QtCore.QPoint(0, info.height())
        )


class QProfileInfo(QtW.QWidget):
    def __init__(self, current_profile_name: str):
        super().__init__()
        label_texts = []
        for path in profile_dir().iterdir():
            if path.stem == current_profile_name:
                label_texts.append(f"&gt; <b>{path.stem}</b>")
            else:
                label_texts.append(f"&nbsp;&nbsp; {path.stem}")
        label_text = "<br>".join(label_texts)
        label = QtW.QLabel(label_text)
        label.setTextFormat(QtCore.Qt.TextFormat.RichText)
        label.setTextInteractionFlags(
            QtCore.Qt.TextInteractionFlag.TextBrowserInteraction
        )
        layout = QtW.QVBoxLayout(self)
        layout.addWidget(label)
