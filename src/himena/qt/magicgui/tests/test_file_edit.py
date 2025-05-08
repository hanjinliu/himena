from pathlib import Path

import pytest
from magicgui.types import FileDialogMode
from himena.qt.magicgui import _file_edit
from himena.qt.magicgui._file_edit import FileEdit, QFileEdit

def test_file_edit(monkeypatch):
    fe = FileEdit()
    assert isinstance(fe.native, QFileEdit)
    fe.set_value(__file__)
    assert fe.value == Path(__file__)
    with pytest.raises(ValueError):
        fe.set_value([__file__, Path(__file__).parent])
    fe.native._mode = FileDialogMode.EXISTING_FILES
    fe.set_value([__file__, Path(__file__).parent])
    assert fe.value == [Path(__file__), Path(__file__).parent]
    monkeypatch.setattr(_file_edit, "show_file_dialog", lambda *_, **__: __file__)
    fe.native._open_file_dialog()
