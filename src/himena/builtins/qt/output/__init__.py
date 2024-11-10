"""Builtin standard output plugin."""

from himena.plugins import register_dock_widget


@register_dock_widget(
    title="Output",
    menus=["tools"],
    area="right",
    keybindings=["Ctrl+Shift+U"],
    singleton=True,
    command_id="builtins:output",
)
def install_output_widget(ui):
    """Standard output widget."""
    from himena.builtins.qt.output._widget import get_interface

    return get_interface().widget
