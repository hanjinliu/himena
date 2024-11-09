"""Builtin File tree plugin."""

from himena.plugins import get_plugin_interface

__himena_plugin__ = get_plugin_interface("tools")


@__himena_plugin__.register_dock_widget(
    title="File tree",
    area="left",
    keybindings="Ctrl+Shift+E",
    command_id="builtins:filetree",
    singleton=True,
)
def make_file_tree_widget(ui):
    """Open a file tree widget to efficiently open files in a workspace."""
    from himena.builtins.qt.filetree._widget import QWorkspaceWidget

    filetree = QWorkspaceWidget()
    filetree.fileDoubleClicked.connect(ui.read_file)
    return filetree
