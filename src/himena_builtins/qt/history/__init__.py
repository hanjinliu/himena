from himena.plugins import register_dock_widget_action, add_default_status_tip
from himena.consts import MenuId

add_default_status_tip(
    short="command history",
    long="Ctrl+Shift+H to check, copy and re-run executed commands",
)


@register_dock_widget_action(
    title="Command History",
    menus=[MenuId.TOOLS_DOCK, MenuId.TOOLS, MenuId.CORNER],
    area="right",
    keybindings=["Ctrl+Shift+H"],
    singleton=True,
    command_id="builtins:command-history",
    icon="foundation:list",
)
def install_command_history(ui):
    """A command history widget for viewing and executing commands."""
    from himena_builtins.qt.history._widget import QCommandHistory

    return QCommandHistory(ui)
