"""Builtin QtConsole plugin."""

from himena.plugins import get_plugin_interface

__himena_plugin__ = get_plugin_interface("tools")


@__himena_plugin__.register_dock_widget(
    title="Console",
    area="bottom",
    keybindings=["Ctrl+Shift+C"],
    singleton=True,
    command_id="builtins:console",
)
def install_console(ui):
    """Python interpreter widget."""
    from himena.builtins.qt.console._widget import QtConsole

    console = QtConsole()
    console.connect_parent(ui)
    return console
