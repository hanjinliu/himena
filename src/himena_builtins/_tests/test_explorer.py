from pathlib import Path
from qtpy import QtWidgets as QtW
from qtpy.QtCore import Qt
from unittest.mock import MagicMock
from himena.testing import choose_one_dialog_response
from himena.testing.dialog import file_dialog_response
from himena.workflow import LocalReaderMethod
from himena_builtins.qt.explorer._base import QBaseRemoteExplorerWidget
from himena_builtins.qt.explorer._widget import QExplorerWidget
from himena_builtins.qt.explorer._widget_ssh import QSSHRemoteExplorerWidget

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
def test_ssh_widget(qtbot: QtBot, himena_ui, tmpdir):
    tmpdir = Path(tmpdir)
    widget = QSSHRemoteExplorerWidget(himena_ui)
    qtbot.add_widget(widget)
    widget.show()
    widget._file_list_widget._make_context_menu()
    widget._file_list_widget._apply_filter("a")
    assert widget._filter_widget.isHidden()
    qtbot.keyClick(widget, Qt.Key.Key_F, Qt.KeyboardModifier.ControlModifier)
    assert widget._filter_widget.isVisible()
    qtbot.keyClick(widget._filter_widget, Qt.Key.Key_Escape)
    assert widget._filter_widget.isHidden()
    with file_dialog_response(himena_ui, tmpdir):
        widget._file_list_widget._download_items([])
    widget._file_list_widget._download_items([], download_dir=tmpdir)

class QTestRemoteExplorerWidget(QBaseRemoteExplorerWidget):
    def _make_reader_method(self, path: Path, is_dir: bool) -> LocalReaderMethod:
        return LocalReaderMethod(path=path)

    def _iter_file_items(self, path: str):
        if path == "~":
            path = Path.home()
        for p in Path(path).iterdir():
            if p.is_dir():
                typ = "d"
            else:
                typ = "f"
            item = QtW.QTreeWidgetItem([p.name] + ["", "", "", "", "", typ, ""])
            yield item

    def _get_file_type(self, path: str) -> str:
        if Path(path).is_dir():
            return "d"
        else:
            return "f"

    def _move_files(self, src: str, dst: str) -> None:
        Path(src).rename(dst)

    def _trash_files(self, paths):
        pass  # do nothing

    def _send_file(self, src: Path, dst_remote: str, is_dir: bool = False):
        Path(dst_remote).write_bytes(src.read_bytes())

    def _make_reader_method_from_str(self, line: str, is_dir: bool) -> LocalReaderMethod:
        # X@Y:<path>
        path = line
        return LocalReaderMethod(path=path)

def test_remote_base_widget(qtbot: QtBot, himena_ui, tmpdir):
    # root
    #  ├── Dir
    #  │   └── c.txt (abc)
    #  ├── a.txt (a)
    #  ├── b.txt (bb)
    tmpdir = Path(tmpdir)
    tmpdir.joinpath("Dir").mkdir()
    tmpdir.joinpath("a.txt").write_text("a")
    tmpdir.joinpath("b.txt").write_text("bb")
    tmpdir.joinpath("Dir", "c.txt").write_text("abc")
    widget = QTestRemoteExplorerWidget(himena_ui)
    widget._force_sync = True
    assert len(list(widget._iter_file_items(tmpdir.as_posix()))) == 3
    widget._set_current_path(tmpdir)
    widget._refresh_pwd()
    widget._on_pwd_edited()
    QtW.QApplication.processEvents()
    QtW.QApplication.processEvents()
    assert widget._file_list_widget.topLevelItemCount() == 3
    widget._copy_item_paths([widget._file_list_widget.topLevelItem(i) for i in range(3)])
    qtbot.add_widget(widget)
    widget.show()
    widget._file_list_widget._make_context_menu()

    widget._file_list_widget._apply_filter("a")
    assert widget._filter_widget.isHidden()
    qtbot.keyClick(widget, Qt.Key.Key_F, Qt.KeyboardModifier.ControlModifier)
    assert widget._filter_widget.isVisible()
    qtbot.keyClick(widget._filter_widget, Qt.Key.Key_Escape)
    assert widget._filter_widget.isHidden()
    with file_dialog_response(himena_ui, tmpdir / "Dir"):
        widget._file_list_widget._download_items([], download_dir=tmpdir / "Dir")
    widget._file_list_widget._download_items([], download_dir=tmpdir / "Dir")
    widget._get_file_type(tmpdir / "a.txt")
    mime = widget._make_mimedata_for_items([widget._file_list_widget.topLevelItem(1)])
    widget._read_and_add_model(tmpdir / "a.txt")
    widget.readers_from_mime(mime)
