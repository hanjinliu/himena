"""Builtin standard output plugin."""

from typing import TYPE_CHECKING
from himena.plugins import register_dock_widget

if TYPE_CHECKING:
    from himena.widgets import MainWindow


@register_dock_widget(
    title="Output",
    menus=["tools/dock"],
    area="right",
    keybindings=["Ctrl+Shift+U"],
    singleton=True,
    command_id="builtins:output",
    plugin_configs={
        "format": {
            "value": "%(levelname)s:%(message)s",
            "tooltip": "The logger format",
        },
        "date_format": {
            "value": "%Y-%m-%d %H:%M:%S",
            "tooltip": "The logger date format",
        },
    },
)
def install_output_widget(ui: "MainWindow"):
    """Standard output widget."""
    from himena_builtins.qt.output._widget import get_widget

    return get_widget(ui.model_app.name)
