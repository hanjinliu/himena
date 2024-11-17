from himena.plugins._signature import configure_gui
from himena.plugins.io import register_reader_provider, register_writer_provider
from himena.plugins.actions import (
    register_function,
    register_dialog,
    register_dock_widget,
    configure_submenu,
    AppActionRegistry,
)
from himena.plugins.install import install_plugins, dry_install_plugins

__all__ = [
    "configure_gui",
    "get_plugin_interface",
    "install_plugins",
    "dry_install_plugins",
    "register_reader_provider",
    "register_writer_provider",
    "register_function",
    "register_dialog",
    "register_dock_widget",
    "configure_submenu",
    "AppActionRegistry",
]
