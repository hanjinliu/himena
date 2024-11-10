from .io import register_reader_provider, register_writer_provider
from .actions import (
    register_function,
    register_dialog,
    register_dock_widget,
    register_new_provider,
)
from .install import install_plugins, dry_install_plugins

__all__ = [
    "get_plugin_interface",
    "install_plugins",
    "dry_install_plugins",
    "register_reader_provider",
    "register_writer_provider",
    "register_function",
    "register_dialog",
    "register_dock_widget",
    "register_new_provider",
]
