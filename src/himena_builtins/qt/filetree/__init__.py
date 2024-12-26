"""Builtin File tree plugin."""

from himena.plugins import register_dock_widget


@register_dock_widget(
    title="File Explorer",
    menus=["tools"],
    area="left",
    keybindings="Ctrl+Shift+E",
    command_id="builtins:filetree",
    singleton=True,
)
def make_file_tree_widget(ui):
    """Open a file tree widget to efficiently open files in a workspace."""
    from himena_builtins.qt.filetree._widget import QWorkspaceWidget

    filetree = QWorkspaceWidget()
    filetree.fileDoubleClicked.connect(ui.read_file)
    return filetree


@register_dock_widget(
    title="File Explorer (SSH)",
    menus=["tools"],
    area="left",
    command_id="builtins:filetree-ssh",
    singleton=True,
)
def make_file_tree_ssh_widget(ui):
    """Open a file tree widget to efficiently open files in a workspace."""
    from himena_builtins.qt.filetree._widget_ssh import QSSHRemoteWorkspaceWidget

    filetree = QSSHRemoteWorkspaceWidget(ui)
    return filetree
