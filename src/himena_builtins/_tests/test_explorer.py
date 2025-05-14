from pathlib import Path
from qtpy.QtCore import Qt
from unittest.mock import MagicMock
from himena.testing import choose_one_dialog_response
from himena_builtins.qt.explorer._widget import QExplorerWidget
from himena_builtins.qt.explorer._widget_ssh import QSSHRemoteExplorerWidget, _make_ls_args, _make_get_type_args

from pytestqt.qtbot import QtBot


def test_workspace_widget(qtbot: QtBot, himena_ui, tmpdir):
    tmpdir = Path(tmpdir)
    mock = MagicMock()
    widget = QExplorerWidget(himena_ui)
    qtbot.add_widget(widget)
    widget.open_file_requested.connect(mock)

    widget._root.set_root_path(tmpdir)  # now it's safe to move files
    widget._file_tree._make_context_menu(widget._file_tree.model().index(0, 0))
    widget._file_tree._make_drag()
    mock.assert_not_called()

    with choose_one_dialog_response(himena_ui, "Replace"):
        widget._file_tree._paste_file([Path(__file__)], tmpdir, is_copy=True)
        assert (tmpdir / Path(__file__).name).exists()
        widget._file_tree._paste_file([tmpdir / Path(__file__).name], tmpdir, is_copy=True)


    # TODO: not working ...
    # qtree = widget._workspace_tree
    # file_index = qtree.indexBelow(qtree.model().index(0, 0))
    # qtbot.mouseDClick(
    #     qtree.viewport(),
    #     QtCore.Qt.MouseButton.LeftButton,
    #     QtCore.Qt.KeyboardModifier.NoModifier,
    #     qtree.visualRect(file_index).center(),
    # )
    # mock.assert_called_once()
    # assert isinstance(mock.call_args[0][0], Path)

def test_ssh_args():
    assert _make_ls_args("HOST", "PATH") == [
        "ssh", "-p", "22", "HOST", "ls", "PATH/", "-AF"
    ]
    assert _make_get_type_args("HOST", "PATH") == [
        "ssh", "-p", "22", "HOST", "stat", "PATH", "--format='%F'"
    ]

def test_ssh_widget(qtbot: QtBot, himena_ui):
    widget = QSSHRemoteExplorerWidget(himena_ui)
    qtbot.add_widget(widget)
    widget.show()
    widget._file_list_widget._make_context_menu()
    widget._apply_filter("a")
    assert widget._filter_widget.isHidden()
    qtbot.keyClick(widget, Qt.Key.Key_F, Qt.KeyboardModifier.ControlModifier)
    assert widget._filter_widget.isVisible()
    qtbot.keyClick(widget._filter_widget, Qt.Key.Key_Escape)
    assert widget._filter_widget.isHidden()
