from pathlib import Path
from unittest.mock import MagicMock
from royalapp.builtins.qt.filetree._widget import QWorkspaceWidget
from pytestqt.qtbot import QtBot


def test_workspace_widget(qtbot: QtBot):
    mock = MagicMock()
    widget = QWorkspaceWidget()
    qtbot.add_widget(widget)
    widget.fileDoubleClicked.connect(mock)
    widget._root._set_root_path(Path(__file__).parent)
    mock.assert_not_called()
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
