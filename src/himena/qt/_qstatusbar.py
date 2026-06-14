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
        self._profile_btn = btn = QtW.QPushButton(f"{parent._app.name}")
        btn.setToolTip("Application profile")
        btn.setObjectName("profileButton")
        btn.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(self._open_profile_info)
        btn.setSizePolicy(QtW.QSizePolicy.Policy.Maximum, QtW.QSizePolicy.Policy.Fixed)

        # NOTE: status bar already has a size grip.
        self.addPermanentWidget(btn)

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
