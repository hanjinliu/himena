"""Builtin standard output plugin."""

from typing import TYPE_CHECKING
from dataclasses import dataclass
from himena.plugins import register_dock_widget_action, config_field

if TYPE_CHECKING:
    from himena.widgets import MainWindow


@dataclass
class OutputConfig:
    """Configuration for the output widget."""

    format: str = config_field(
        default="%(levelname)s:%(message)s",
        tooltip="The logger format",
    )
    date_format: str = config_field(
        default="%Y-%m-%d %H:%M:%S",
        tooltip="The logger date format",
    )


@register_dock_widget_action(
    title="Output",
    area="right",
    keybindings=["Ctrl+Shift+U"],
    singleton=True,
    command_id="builtins:output",
    plugin_configs=OutputConfig(),
)
def install_output_widget(ui: "MainWindow"):
    """Standard output widget."""
    from himena_builtins.qt.output._widget import get_widget

    return get_widget(ui.model_app.name)
