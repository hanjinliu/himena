"""Builtin QtConsole plugin."""

from himena.plugins import register_dock_widget


@register_dock_widget(
    title="Console",
    menus=["tools/dock"],
    area="bottom",
    keybindings=["Ctrl+Shift+C"],
    singleton=True,
    command_id="builtins:console",
    plugin_configs={
        "main_window_symbol": {
            "value": "ui",
            "tooltip": "Variable name used for the main window instance.",
        },
    },
)
def install_console(ui):
    """Python interpreter widget."""
    from himena_builtins.qt.console._widget import QtConsole

    return QtConsole(ui)
