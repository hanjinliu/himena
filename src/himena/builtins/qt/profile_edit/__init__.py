"""Builtin QtConsole plugin."""

from himena.plugins import register_dialog


@register_dialog(
    title="Edit Profile",
    menus=["tools"],
    command_id="builtins:profile_edit",
)
def edit_profile():
    """Python interpreter widget."""
    from himena.builtins.qt.profile_edit._widget import QProfileEditor

    return QProfileEditor()
