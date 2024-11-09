"""Builtin QtConsole plugin."""

from himena.plugins import get_plugin_interface

__himena_plugin__ = get_plugin_interface("tools")


@__himena_plugin__.register_dialog(
    title="Edit Profile",
    command_id="builtins:profile_edit",
)
def edit_profile():
    """Python interpreter widget."""
    from himena.builtins.qt.profile_edit._widget import QProfileEditor

    return QProfileEditor()
