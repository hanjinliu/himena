from pathlib import Path
from tempfile import TemporaryDirectory
from royalapp import new_window

def test_new_window():
    win = new_window(app="test_new_window")
    assert len(win.tabs) == 0
    with TemporaryDirectory() as tmp:
        path = Path(tmp) / "test.txt"
        path.write_text("Hello, World!")
        win.read_file(path)
    assert len(win.tabs) == 1
    assert len(win.tabs[0]) == 1
    with TemporaryDirectory() as tmp:
        path = Path(tmp) / "test.txt"
        path.write_text("Hello, World! 2")
        win.read_file(path)
    assert len(win.tabs) == 1
    assert len(win.tabs[0]) == 2
    win.add_tab("New tab")
    assert len(win.tabs) == 2
    assert len(win.tabs.current()) == 0
    assert win.tabs.current().title == "New tab"

def test_builtin_dock_commands():
    win = new_window(app="test_builtin_dock_commands")
    win.exec_action("builtins:console")
    win.exec_action("builtins:filetree")
