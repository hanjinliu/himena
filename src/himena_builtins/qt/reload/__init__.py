"""Builtin Qt hot reloader."""

from typing import TYPE_CHECKING
from dataclasses import dataclass
from himena.plugins import register_dock_widget_action, config_field
from himena.consts import MenuId
from himena.qt._utils import get_stylesheet_path

if TYPE_CHECKING:
    from himena.qt import MainWindowQt


@dataclass
class QtReloadConfig:
    default_modules: str = config_field(
        default="himena",
        tooltip="Comma-separated list of modules to reload by default.",
    )


@register_dock_widget_action(
    title="[Dev] Hot Reload",
    area="right",
    menus=[MenuId.TOOLS_DOCK],
    singleton=True,
    # plugin_configs=QtReloadConfig(),
    command_id="builtins:hot-reload",
)
def install_qtreload_widget(ui: "MainWindowQt"):
    """Hot reloader widget."""
    from qtreload import QtReloadWidget

    widget = QtReloadWidget(["himena"])

    @widget.evt_stylesheet.connect
    def _reload_stylesheet():
        """Reload stylesheet."""
        stylesheet = ui.theme.format_text(get_stylesheet_path().read_text())
        ui._backend_main_window.setStyleSheet(stylesheet)

    return widget
