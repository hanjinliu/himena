"""Builtin File tree plugin."""

from royalapp.plugins import get_plugin_interface

__royalapp_plugin__ = get_plugin_interface("tools")


@__royalapp_plugin__.register_dock_widget(
    title="File tree",
    area="left",
    keybindings="Ctrl+Shift+E",
    command_id="builtins:filetree",
    singleton=True,
)
def make_file_tree_widget(ui):
    """Open a file tree widget to efficiently open files in a workspace."""
    from royalapp.builtins.qt.filetree._widget import QWorkspaceWidget

    filetree = QWorkspaceWidget()
    filetree.fileDoubleClicked.connect(ui.read_file)
    return filetree
