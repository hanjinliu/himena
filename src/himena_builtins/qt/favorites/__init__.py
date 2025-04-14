from himena.plugins import (
    register_dock_widget_action,
    add_default_status_tip,
)
from himena.consts import MenuId
from himena_builtins.qt.favorites._config import FavoriteCommandsConfig

add_default_status_tip(
    short="favorites",
    long="Ctrl+Shift+F to edit and run favorite commands",
)


@register_dock_widget_action(
    title="Favorite Commands",
    menus=[MenuId.TOOLS_DOCK, MenuId.TOOLS, MenuId.CORNER],
    area="right",
    keybindings=["Ctrl+Shift+F"],
    singleton=True,
    command_id="builtins:favorite-commands",
    plugin_configs=FavoriteCommandsConfig(),
    icon="mdi:favorite-circle",
)
def install_favorite_commands(ui):
    """Show the favorite commands."""
    from himena_builtins.qt.favorites._widget import QFavoriteCommands

    return QFavoriteCommands(ui)
