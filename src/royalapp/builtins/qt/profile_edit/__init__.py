"""Builtin QtConsole plugin."""

from royalapp.plugins import get_plugin_interface

__royalapp_plugin__ = get_plugin_interface()


@__royalapp_plugin__.register_dialog(
    title="Edit Profile",
    command_id="builtins:profile_edit",
)
def edit_profile():
    """Python interpreter widget."""
    from royalapp.builtins.qt.profile_edit._widget import QProfileEditor

    return QProfileEditor()
