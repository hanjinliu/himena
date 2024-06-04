"""Builtin QtConsole plugin."""

from royalapp.plugins import get_plugin_interface

__royalapp_plugin__ = get_plugin_interface()


@__royalapp_plugin__.register_dock_widget(
    title="Console",
    area="bottom",
    keybindings=["Ctrl+Shift+C"],
    singleton=True,
)
def install_console(ui):
    """Python interpreter widget."""
    from royalapp.builtins.qt.console._widget import QtConsole

    console = QtConsole()
    console.connect_parent(ui)
    return console
