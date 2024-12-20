from himena.plugins.widget_class import (
    register_widget_class,
    get_widget_class,
    register_previewer_class,
)
from himena.plugins._checker import validate_protocol
from himena.plugins._signature import configure_gui
from himena.plugins.io import register_reader_provider, register_writer_provider
from himena.plugins.actions import (
    register_function,
    register_dock_widget,
    configure_submenu,
    register_conversion_rule,
    AppActionRegistry,
)
from himena.plugins.install import install_plugins

__all__ = [
    "get_widget_class",
    "register_previewer_class",
    "validate_protocol",
    "configure_gui",
    "get_plugin_interface",
    "install_plugins",
    "register_reader_provider",
    "register_writer_provider",
    "register_function",
    "register_dock_widget",
    "register_widget_class",
    "register_conversion_rule",
    "configure_submenu",
    "AppActionRegistry",
]
