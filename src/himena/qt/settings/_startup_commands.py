from __future__ import annotations

from qtpy import QtWidgets as QtW, QtCore
from typing import TYPE_CHECKING
from himena.qt.settings._shared import QInstruction

if TYPE_CHECKING:
    from himena.widgets import MainWindow


class QStartupCommandsPanel(QtW.QWidget):
    """Widget to edit the startup commands."""

    def __init__(self, ui: MainWindow):
        super().__init__()
        self._ui = ui
        self._instruction = QInstruction(
            "List command IDs to be executed at startup.",
        )
        self._text_edit = QtW.QPlainTextEdit(self)
        self._text_edit.setPlainText("\n".join(self._ui.app_profile.startup_commands))
        self._footer = QtW.QWidget(self)
        _footer_layout = QtW.QHBoxLayout(self._footer)
        _footer_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        self._apply_button = QtW.QPushButton("Apply", self._footer)
        self._apply_button.clicked.connect(self._apply_changes)
        self._msg_label = QtW.QLabel(self._footer)
        self._msg_label.setMaximumWidth(280)
        _footer_layout.setContentsMargins(0, 0, 0, 0)
        _footer_layout.addWidget(self._msg_label)
        _footer_layout.addWidget(self._apply_button)
        layout = QtW.QVBoxLayout(self)
        layout.addWidget(self._instruction)
        layout.addWidget(self._text_edit)
        layout.addWidget(self._footer)
        self._text_edit.textChanged.connect(self._on_text_changed)

    def _apply_changes(self):
        commands: list[str] = []
        commands_unknown: list[str] = []
        app = self._ui.model_app
        for line in self._text_edit.toPlainText().splitlines():
            line = line.strip()
            if line not in app.commands:
                commands_unknown.append(line)
            commands.append(line)
        if commands_unknown:
            self._msg_label.setText(f"Unknown commands: {', '.join(commands_unknown)}")
        else:
            self._msg_label.setText("Changes applied.")
        self._ui.app_profile.startup_commands = commands
        self._ui.app_profile.save()

    def _on_text_changed(self):
        self._msg_label.clear()
