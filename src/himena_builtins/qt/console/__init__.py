"""Builtin QtConsole plugin."""

from dataclasses import dataclass
from typing import Literal
from himena.widgets import MainWindow
from himena.plugins import (
    register_dock_widget_action,
    add_default_status_tip,
    config_field,
)

add_default_status_tip(
    short="command palette",
    long="Ctrl+Shift+P to search for all the registered commands",
)


@dataclass
class ConsoleConfig:
    """Configuration for the console."""

    main_window_symbol: str = config_field(
        default="ui",
        tooltip="Variable name used for the main window instance",
    )
    exit_app_from_console: bool = config_field(
        default=True,
        tooltip="Use the `exit` IPython magic to exit the application.",
    )
    matplotlib_backend: Literal["inline", "himena_builtins"] = config_field(
        default="inline",
        tooltip="Plot backend when the script is executed in the console.",
    )

    @property
    def mpl_backend(self) -> str:
        if self.matplotlib_backend == "himena_builtins":
            from himena_builtins.qt.plot import BACKEND_HIMENA

            return BACKEND_HIMENA
        return self.matplotlib_backend


@register_dock_widget_action(
    title="Console",
    area="bottom",
    keybindings=["Ctrl+Shift+C"],
    singleton=True,
    command_id="builtins:console",
    plugin_configs=ConsoleConfig(),
)
def install_console(ui: MainWindow):
    """Python interpreter widget."""
    from himena_builtins.qt.console._widget import QtConsole

    ui.set_status_tip("Opening Python console ...", 2, process_event=True)
    return QtConsole.get_or_create(ui)
