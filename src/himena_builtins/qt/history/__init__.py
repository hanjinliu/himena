from himena.plugins import register_dock_widget


@register_dock_widget(
    title="Command History",
    menus=["tools"],
    area="right",
    keybindings=["Ctrl+Shift+H"],
    singleton=True,
    command_id="builtins:command-history",
)
def install_command_history(ui):
    """A command history widget for viewing and executing command."""
    from himena_builtins.qt.history._widget import QCommandHistory

    return QCommandHistory(ui)
