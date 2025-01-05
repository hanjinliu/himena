from himena.plugins import register_dock_widget_action


@register_dock_widget_action(
    title="Command History",
    menus=["tools/dock"],
    area="right",
    keybindings=["Ctrl+Shift+H"],
    singleton=True,
    command_id="builtins:command-history",
)
def install_command_history(ui):
    """A command history widget for viewing and executing command."""
    from himena_builtins.qt.history._widget import QCommandHistory

    return QCommandHistory(ui)
