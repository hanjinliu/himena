from pathlib import Path

from qtpy import QtCore
import pytest
from magicgui.types import FileDialogMode
from himena.qt.magicgui import _file_edit
from himena.qt.magicgui._file_edit import FileEdit, QFileEdit

_directory = str(Path(__file__).parent)

def test_file_edit():
    fe = FileEdit()
    assert isinstance(fe.native, QFileEdit)
    fe.set_value(__file__)
    assert fe.value == Path(__file__)
    fe.set_value(None)
    assert fe.value is None
    with pytest.raises(ValueError):
        fe.set_value([__file__, Path(__file__).parent])
    fe.native._mode = FileDialogMode.EXISTING_FILES
    fe.set_value([__file__, Path(__file__).parent])
    assert fe.value == [Path(__file__), Path(__file__).parent]

def test_open_file_dialog(monkeypatch):
    fe = FileEdit()
    assert isinstance(fe.native, QFileEdit)
    fe.native._mode = FileDialogMode.EXISTING_FILE
    monkeypatch.setattr(_file_edit, "show_file_dialog", lambda *_, **__: __file__)
    fe.native._open_file_dialog()
    fe.native._mode = FileDialogMode.EXISTING_FILES
    monkeypatch.setattr(_file_edit, "show_file_dialog", lambda *_, **__: [__file__, _directory])
    fe.native._open_file_dialog()
    fe.native._mode = FileDialogMode.EXISTING_DIRECTORY
    monkeypatch.setattr(_file_edit, "show_file_dialog", lambda *_, **__: _directory)
    fe.native._open_file_dialog()
    fe.native._mode = FileDialogMode.OPTIONAL_FILE
    monkeypatch.setattr(_file_edit, "show_file_dialog", lambda *_, **__: __file__)
    fe.native._open_file_dialog()

def test_accept_urls():
    fe = FileEdit()
    assert isinstance(fe.native, QFileEdit)
    fe.native._mode = FileDialogMode.EXISTING_FILE
    fe.native._accept_urls([QtCore.QUrl(__file__)])
    fe.native._set_urls([QtCore.QUrl(__file__)])
    fe.native._mode = FileDialogMode.EXISTING_FILES
    fe.native._accept_urls([QtCore.QUrl(__file__), QtCore.QUrl(_directory)])
    fe.native._set_urls([QtCore.QUrl(__file__), QtCore.QUrl(_directory)])
    fe.native._mode = FileDialogMode.EXISTING_DIRECTORY
    fe.native._accept_urls([QtCore.QUrl(_directory)])
    fe.native._set_urls([QtCore.QUrl(_directory)])
