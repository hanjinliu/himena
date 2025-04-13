"""Builtin File explorer plugin."""

import sys
from dataclasses import dataclass, field
from himena.plugins import register_dock_widget_action, add_default_status_tip

add_default_status_tip(
    short="File Explorer",
    long="Ctrl+Shift+E to open a file explorer widget on the left.",
)


@dataclass
class FileExplorerConfig:
    allow_drop_data_to_save: bool = field(
        default=True,
        metadata={"tooltip": "Allow dropping data opened in the main window to save."},
    )
    allow_drop_file_to_move: bool = field(
        default=True, metadata={"tooltip": "Allow dropping files to move."}
    )


@dataclass
class FileExplorerSSHConfig:
    default_host: str = field(
        default="", metadata={"tooltip": "The default host name or IP address"}
    )
    default_user: str = field(default="", metadata={"tooltip": "The default user name"})
    default_port: int = field(
        default=22, metadata={"tooltip": "The default port number"}
    )
    default_use_wsl: bool = field(
        default=False,
        metadata={
            "tooltip": "Use WSL to connect to the host in Windows",
            "enabled": sys.platform == "win32",
        },
    )
    default_protocol: str = field(
        default="rsync",
        metadata={"tooltip": "The default protocol to use (rsync or scp)"},
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
def make_file_explorer_ssh_widget(ui):
    """Open a remote file explorer widget as a dock widget."""
    from himena_builtins.qt.explorer._widget_ssh import QSSHRemoteExplorerWidget

    return QSSHRemoteExplorerWidget(ui)
