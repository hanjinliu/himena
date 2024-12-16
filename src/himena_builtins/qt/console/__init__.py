"""Builtin QtConsole plugin."""

from himena.plugins import register_dock_widget


@register_dock_widget(
    title="Console",
    menus=["tools"],
    area="bottom",
    keybindings=["Ctrl+Shift+C"],
    singleton=True,
    command_id="builtins:console",
)
def install_console(ui):
    """Python interpreter widget."""
    from qtpy.QtWidgets import QApplication
    from himena_builtins.qt.console._widget import QtConsole

    console = QtConsole()
    console.connect_parent(ui)
    QApplication.processEvents()
    return console
