"""Builtin standard output plugin."""

from himena.plugins import get_plugin_interface

__himena_plugin__ = get_plugin_interface("tools")


@__himena_plugin__.register_dock_widget(
    title="Output",
    area="bottom",
    keybindings=["Ctrl+Shift+U"],
    singleton=True,
    command_id="builtins:output",
)
def install_output_widget(ui):
    """Standard output widget."""
    from himena.builtins.qt.output._widget import get_interface

    return get_interface().widget
