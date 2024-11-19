from __future__ import annotations

from typing import TYPE_CHECKING
from himena.plugins import register_function

if TYPE_CHECKING:
    from himena.widgets import MainWindow


@register_function(
    title="Settings ...",
    menus=["tools"],
    command_id="builtins:profile_edit",
    keybindings=["Ctrl+,"],
)
def edit_profile(ui: MainWindow):
    """Open a dialog to edit the application profile."""
    from himena.builtins.qt.profile_edit._widget import QProfileEditor

    return QProfileEditor(ui.model_app).exec()
