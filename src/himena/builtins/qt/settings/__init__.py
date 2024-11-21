from __future__ import annotations

from typing import TYPE_CHECKING
from himena.plugins import register_function

if TYPE_CHECKING:
    from himena.widgets import MainWindow


@register_function(
    title="Settings ...",
    menus=["tools"],
    command_id="builtins:settings",
    keybindings=["Ctrl+,"],
)
def show_setting_dialog(ui: MainWindow):
    """Open a dialog to edit the application profile."""
    from himena.builtins.qt.settings._widget import QSettingsDialog

    return QSettingsDialog(ui).exec()
