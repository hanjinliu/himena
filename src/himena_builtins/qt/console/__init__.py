"""Builtin QtConsole plugin."""

from dataclasses import dataclass, field
from himena.plugins import register_dock_widget_action


@dataclass
class ConsoleConfig:
    """Configuration for the console."""

    main_window_symbol: str = field(
        default="ui",
        metadata={"tooltip": "Variable name used for the main window instance."},
    )
    exit_app_from_console: bool = field(
        default=True,
        metadata={"tooltip": "Use the `exit` IPython magic to exit the application."},
    )


@register_dock_widget_action(
    title="Console",
    menus=["tools/dock"],
    area="bottom",
    keybindings=["Ctrl+Shift+C"],
    singleton=True,
    command_id="builtins:console",
    plugin_configs=ConsoleConfig(),
)
def install_console(ui):
    """Python interpreter widget."""
    from himena_builtins.qt.console._widget import QtConsole

    return QtConsole(ui)
