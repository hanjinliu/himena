from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING
from qtpy import QtWidgets as QtW, QtCore
from himena.profile import profile_dir

if TYPE_CHECKING:
    from himena.qt._qmain_window import QMainWindow


class QStatusBar(QtW.QStatusBar):
    """Custom status bar."""

    def __init__(self, parent: QMainWindow):
        super().__init__(parent)
        self._profile_btn = QtW.QPushButton(f"{parent._app.name}")
        self._profile_btn.setToolTip("Application profile")
        self._profile_btn.setObjectName("profileButton")
        self._profile_btn.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self._profile_btn.clicked.connect(self._open_profile_info)

        # NOTE: status bar already has a size grip.
        layout: QtW.QHBoxLayout = self.layout()
        layout.setSpacing(0)
        layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        layout.insertWidget(
            1, self._profile_btn, alignment=QtCore.Qt.AlignmentFlag.AlignRight
        )

    def parentWidget(self) -> QMainWindow:
        return super().parentWidget()

    def _open_profile_info(self) -> None:
        """Open the profile info."""
        cur = self._profile_btn.text()
        choices: list[tuple[str, str]] = []
        for path in profile_dir().iterdir():
            if path.stem == cur:
                choices.append((f"{cur} (current)", cur))
            else:
                choices.append((path.stem, path.stem))

        ui = self.parentWidget()._himena_main_window
        if resp := ui.exec_choose_one_dialog(
            message="Choose another profile to open an new window with it.",
            choices=choices,
            how="palette",
        ):
            socket = ui.socket_info
            if resp != cur:
                if len(list(ui.iter_windows())) == 0 or ui.exec_choose_one_dialog(
                    title="Close this app?",
                    message="There are still windows open. Do you want to keep this application open?",
                    choices=[("Yes, keep it open", False), ("No, close", True)],
                    how="buttons",
                ):
                    ui.close()
                else:
                    ui.set_status_tip(
                        f"Launching a new application with the profile {resp!r}",
                        duration=5,
                    )
            else:
                ui.set_status_tip(
                    "Launching a new application with the same profile", duration=5
                )
            subprocess.Popen(
                ["himena", resp, "--port", str(socket.port), "--host", socket.host],
            )
