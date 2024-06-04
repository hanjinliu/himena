"""Builtin File tree plugin."""

from royalapp.plugins import get_plugin_interface

__royalapp_plugin__ = get_plugin_interface()


@__royalapp_plugin__.register_dock_widget(title="File tree", area="left")
def make_file_tree_widget(ui):
    """Open a file tree widget to efficiently open files in a workspace."""
    from royalapp.builtins.filetree._widget import QWorkspaceFileTree

    console = QWorkspaceFileTree(ui)
    return console
