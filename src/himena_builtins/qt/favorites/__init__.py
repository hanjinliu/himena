from typing import TYPE_CHECKING
from dataclasses import dataclass
from himena.plugins import (
    register_function,
    register_dock_widget_action,
    add_default_status_tip,
    config_field,
)
from himena.consts import MenuId

if TYPE_CHECKING:
    from himena.widgets import MainWindow


add_default_status_tip(
    short="favorites",
    long="Ctrl+Shift+F to edit and run favorite commands",
)


@dataclass
class FavoriteCommandsConfig:
    """Configuration for the favorite commands widget."""

    commands: list[str] = config_field(
        default_factory=list,
        tooltip="List of favorite commands.",
        widget_type="ListEdit",
        layout="vertical",
        annotation="list[str]",
    )


@register_dock_widget_action(
    title="Favorite Commands",
    area="right",
    keybindings=["Ctrl+Shift+F"],
    singleton=True,
    command_id="builtins:favorite-commands",
    plugin_configs=FavoriteCommandsConfig(),
)
def install_favorite_commands(ui):
    """Show the favorite commands."""
    from himena_builtins.qt.favorites._widget import QFavoriteCommands

    return QFavoriteCommands(ui)


@register_function(
    title="Favorite commands ...",
    menus=[MenuId.TOOLS, MenuId.CORNER],
    command_id="builtins:show-favorite-commands",
    icon="mdi:favorite-circle",
)
def show_favorite_commands(ui: "MainWindow") -> None:
    """Show the favorite commands."""
    ui.exec_action("builtins:favorite-commands")
