from pathlib import Path
from tempfile import TemporaryDirectory
from royalapp import MainWindow

def test_new_window(ui: MainWindow):
    ui.show()
    assert len(ui.tabs) == 0
    with TemporaryDirectory() as tmp:
        path = Path(tmp) / "test.txt"
        path.write_text("Hello, World!")
        ui.read_file(path)
    assert len(ui.tabs) == 1
    assert len(ui.tabs[0]) == 1
    with TemporaryDirectory() as tmp:
        path = Path(tmp) / "test.txt"
        path.write_text("Hello, World! 2")
        ui.read_file(path)
    assert len(ui.tabs) == 1
    assert len(ui.tabs[0]) == 2
    ui.add_tab("New tab")
    assert len(ui.tabs) == 2
    assert len(ui.tabs.current()) == 0
    assert ui.tabs.current().title == "New tab"

def test_builtin_dock_commands(ui: MainWindow):
    ui.show()
    ui.exec_action("new-tab")

    ui.exec_action("builtins:console")
    ui.exec_action("builtins:filetree")
    ui.exec_action("builtins:output")
    ui.exec_action("builtins:new-text")
    ui.exec_action("builtins:fetch-seaborn-test-data")

    ui.exec_action("open-recent")

    ui.exec_action("copy-screenshot")
    ui.exec_action("copy-screenshot-area")
    ui.exec_action("copy-screenshot-window")
    ui.exec_action("quit")
