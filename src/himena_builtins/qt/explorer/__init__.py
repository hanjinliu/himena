"""Builtin File explorer plugin."""

import sys
from himena.plugins import register_dock_widget


@register_dock_widget(
    title="File Explorer",
    menus=["tools/dock"],
    area="left",
    keybindings="Ctrl+Shift+E",
    command_id="builtins:file-explorer",
    singleton=True,
)
def make_file_explorer_widget(ui):
    """Open a file explorer widget as a dock widget."""
    from himena_builtins.qt.explorer._widget import QExplorerWidget

    return QExplorerWidget(ui)


@register_dock_widget(
    title="File Explorer (SSH)",
    menus=["tools/dock"],
    area="left",
    command_id="builtins:file-explorer-ssh",
    singleton=True,
    plugin_configs={
        "default_host": {"value": "", "tooltip": "The default host name or IP address"},
        "default_user": {"value": "", "tooltip": "The default user name"},
        "default_use_wsl": {
            "value": False,
            "tooltip": "Use WSL to connect to the host in Windows",
            "enabled": sys.platform == "win32",
        },
    },
)
def make_file_explorer_ssh_widget(ui):
    """Open a file explorer widget remotely as a dock widget."""
    from himena_builtins.qt.explorer._widget_ssh import QSSHRemoteExplorerWidget

    return QSSHRemoteExplorerWidget(ui)
