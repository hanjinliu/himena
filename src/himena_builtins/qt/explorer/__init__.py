"""Builtin File explorer plugin."""

import sys
from dataclasses import dataclass
from himena.plugins import (
    register_dock_widget_action,
    add_default_status_tip,
    config_field,
)
from himena.widgets import MainWindow

add_default_status_tip(
    short="File Explorer",
    long="Ctrl+Shift+E to open a file explorer widget on the left.",
)


@dataclass
class FileExplorerConfig:
    allow_drop_data_to_save: bool = config_field(
        default=True,
        tooltip="Allow dropping data opened in the main window to save.",
    )
    allow_drop_file_to_move: bool = config_field(
        default=True, tooltip="Allow dropping files to move."
    )


@dataclass
class FileExplorerSSHConfig:
    default_host: str = config_field(
        default="", tooltip="The default host name or IP address"
    )
    default_user: str = config_field(default="", tooltip="The default user name")
    default_port: int = config_field(default=22, tooltip="The default port number")
    default_use_wsl: bool = config_field(
        default=False,
        tooltip="Use WSL to connect to the host in Windows",
        enabled=sys.platform == "win32",
    )
    default_protocol: str = config_field(
        default="rsync",
        tooltip="The default protocol to use (rsync or scp)",
    )


@register_dock_widget_action(
    title="File Explorer",
    area="left",
    keybindings="Ctrl+Shift+E",
    command_id="builtins:file-explorer",
    singleton=True,
    plugin_configs=FileExplorerConfig(),
)
def make_file_explorer_widget(ui):
    """Open a file explorer widget as a dock widget."""
    from himena_builtins.qt.explorer._widget import QExplorerWidget

    return QExplorerWidget(ui)


@register_dock_widget_action(
    title="Remote File Explorer",
    area="left",
    command_id="builtins:file-explorer-ssh",
    singleton=True,
    plugin_configs=FileExplorerSSHConfig(),
)
def make_file_explorer_ssh_widget(ui: MainWindow):
    """Open a remote file explorer widget as a dock widget."""
    from himena_builtins.qt.explorer._widget_ssh import QSSHRemoteExplorerWidget

    ui.set_status_tip("Opening remote file explorer ...", 2, process_event=True)
    return QSSHRemoteExplorerWidget(ui)
