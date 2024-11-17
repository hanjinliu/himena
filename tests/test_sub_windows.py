from pathlib import Path
from tempfile import TemporaryDirectory
from qtpy import QtWidgets as QtW
from himena import MainWindow, anchor
from himena.consts import StandardType
from himena.types import ClipboardDataModel, WidgetDataModel
from himena.qt import register_widget, MainWindowQt
from himena.builtins.qt import widgets as _qtw

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

def test_builtin_commands(ui: MainWindow):
    ui.show()
    ui.exec_action("new-tab")
    assert len(ui.tabs) == 1
    assert len(ui.tabs[0]) == 0
    ui.exec_action("builtins:console")
    ui.exec_action("builtins:filetree")
    ui.exec_action("builtins:output")
    ui.exec_action("builtins:new-text")
    assert len(ui.tabs[0]) == 1
    ui.exec_action("builtins:fetch-seaborn-sample-data")
    ui.exec_action("quit")

def test_io_commands(ui: MainWindow, tmpdir, sample_dir: Path):
    response_open = lambda: [sample_dir / "text.txt"]
    response_save = lambda: Path(tmpdir) / "text_out.txt"
    ui._instructions = ui._instructions.updated(file_dialog_response=response_open)
    ui.exec_action("open-file")
    ui.add_data("Hello", type="text")
    ui._instructions = ui._instructions.updated(file_dialog_response=response_save)
    ui.exec_action("save")
    ui.exec_action("save-as")

    # session
    response_session = lambda: Path(tmpdir) / "a.session.yaml"
    ui._instructions = ui._instructions.updated(file_dialog_response=response_session)
    ui.exec_action("save-session")
    ui.exec_action("load-session")
    ui.exec_action("save-tab-session")

    response_open = lambda: [sample_dir / "table.csv"]
    ui._instructions = ui._instructions.updated(file_dialog_response=response_open)
    ui.exec_action("open-file-using")

def test_window_commands(ui: MainWindowQt, sample_dir: Path):
    ui.exec_action("show-command-palette")
    ui.read_file(sample_dir / "text.txt")
    assert len(ui.tabs) == 1
    assert len(ui.tabs[0]) == 1
    ui._backend_main_window.setFocus()
    ui.exec_action("open-recent")
    ui._backend_main_window.setFocus()

    ui.exec_action("duplicate-window")
    ui.exec_action("duplicate-window")
    assert len(ui.tabs[0]) == 3
    ui.exec_action("rename-window")

    # anchor
    ui.exec_action("anchor-window-top-left")
    ui.exec_action("anchor-window-top-right")
    ui.exec_action("anchor-window-bottom-left")
    ui.exec_action("anchor-window-bottom-right")
    ui.exec_action("unset-anchor")

    # zoom
    ui.exec_action("window-expand")
    ui.exec_action("window-shrink")

    # align
    ui.exec_action("align-window-left")
    ui.exec_action("align-window-right")
    ui.exec_action("align-window-top")
    ui.exec_action("align-window-bottom")
    ui.exec_action("align-window-center")

    # state
    ui.exec_action("minimize-window")
    ui.exec_action("maximize-window")
    ui.exec_action("toggle-full-screen")
    ui.exec_action("toggle-full-screen")
    ui.exec_action("close-window")
    ui.exec_action("show-command-palette")
    ui.exec_action("new")

    ui.read_file(sample_dir / "text.txt")
    assert len(ui.tabs) == 1
    ui.exec_action("full-screen-in-new-tab")
    assert len(ui.tabs) == 2
    assert ui.tabs.current_index == 1

def test_screenshot_commands(ui: MainWindow, sample_dir: Path, tmpdir):
    ui.read_file(sample_dir / "text.txt")

    # copy
    ui.clipboard = ClipboardDataModel(value="", type="text")  # just for initialization
    ui.exec_action("copy-screenshot")
    assert ui.clipboard.type == StandardType.IMAGE
    ui.clipboard = ClipboardDataModel(value="", type="text")  # just for initialization
    ui.exec_action("copy-screenshot-area")
    assert ui.clipboard.type == StandardType.IMAGE
    ui.clipboard = ClipboardDataModel(value="", type="text")  # just for initialization
    ui.exec_action("copy-screenshot-window")
    assert ui.clipboard.type == StandardType.IMAGE

    # save
    ui._instructions = ui._instructions.updated(
        file_dialog_response=lambda: Path(tmpdir) / "screenshot.png"
    )
    ui.exec_action("save-screenshot")
    ui.exec_action("save-screenshot-area")
    ui.exec_action("save-screenshot-window")
    assert Path(tmpdir).joinpath("screenshot.png").exists()

def test_view_menu_commands(ui: MainWindow, sample_dir: Path):
    ui.exec_action("new-tab")
    ui.exec_action("close-tab")
    ui.exec_action("new-tab")
    ui.read_file(sample_dir / "text.txt")
    ui.read_file(sample_dir / "text.txt")
    ui.exec_action("new-tab")
    ui.read_file(sample_dir / "text.txt")
    assert ui.tabs.current_index == 1
    ui.exec_action("goto-last-tab")
    assert ui.tabs.current_index == 0
    assert len(ui.tabs.current()) == 2
    assert ui.tabs.current()[0].state == "normal"
    assert ui.tabs.current()[1].state == "normal"
    ui.exec_action("minimize-other-windows")
    assert ui.tabs.current()[0].state == "min"
    assert ui.tabs.current()[1].state == "normal"
    ui.exec_action("show-all-windows")
    assert ui.tabs.current()[0].state == "normal"
    assert ui.tabs.current()[1].state == "normal"
    ui.exec_action("close-all-windows")
    assert len(ui.tabs.current()) == 0

    # close tab with unsaved
    win0 = ui.read_file(sample_dir / "text.txt")
    win0.widget.set_modified(True)
    win1 = ui.read_file(sample_dir / "table.csv")
    win1.widget.set_modified(True)
    ui.read_file(sample_dir / "text.txt")
    ui.exec_action("close-tab")

def test_tools_menu(ui: MainWindow):
    ui.add_data("a\nb\nc\nbc", type="text")
    ui.tabs[0].current_index = 0
    ui.exec_action("builtins:filter-text", with_params={"include": "b"})
    assert ui.current_window.to_model().value == "b\nbc"
    ui.tabs[0].current_index = 0
    ui.exec_action("builtins:filter-text", with_params={"exclude": "b"})
    assert ui.current_window.to_model().value == "a\nc"
    ui.tabs[0].current_index = 0
    ui.exec_action(
        "builtins:filter-text",
        with_params={"exclude": "b", "case_sensitive": False},
    )

    ui.clear()
    ui.add_data('{"a": [1, 2], "b": null}', type="text.json")
    ui.tabs[0].current_index = 0
    ui.exec_action("builtins:format-json", with_params={})

def test_custom_widget(ui: MainWindow):
    from qtpy.QtWidgets import QLabel

    ui.show()
    label = QLabel("Custom widget test")
    widget = ui.add_widget(label)
    assert len(ui.tabs) == 1
    assert len(ui.tabs[0]) == 1
    widget.title = "New title"
    assert widget.title == "New title"
    widget.rect = (10, 20, 100, 200)
    assert widget.rect == (10, 20, 100, 200)
    widget.anchor = "top-left"
    assert isinstance(widget.anchor, anchor.TopLeftConstAnchor)
    widget.anchor = "top-right"
    assert isinstance(widget.anchor, anchor.TopRightConstAnchor)
    widget.anchor = "bottom-left"
    assert isinstance(widget.anchor, anchor.BottomLeftConstAnchor)
    widget.anchor = "bottom-right"
    assert isinstance(widget.anchor, anchor.BottomRightConstAnchor)
    widget.state = "max"
    assert widget.state == "max"
    widget.state = "min"
    assert widget.state == "min"
    widget.state = "normal"
    assert widget.state == "normal"
    widget.state = "full"
    assert widget.state == "full"

def test_custom_dock_widget(ui: MainWindow):
    from qtpy.QtWidgets import QLabel

    ui.show()
    widget = QLabel("Dock widget test")
    dock = ui.add_dock_widget(widget)
    assert ui.dock_widgets.len()
    assert dock.visible
    dock.visible = False
    assert not dock.visible
    dock.title = "New title"
    assert dock.title == "New title"

def test_fallback_widget(ui: MainWindow):
    from himena.qt.registry._widgets import QFallbackWidget
    model = WidgetDataModel(value=object(), type="unsupported")
    win = ui.add_data_model(model)
    assert isinstance(win.widget, QFallbackWidget)

def test_register_widget(ui: MainWindow):
    from qtpy.QtWidgets import QLabel

    class QCustomTextView(QLabel):
        def update_model(self, model: WidgetDataModel):
            return self.setText(model.value)

    model = WidgetDataModel(value="abc", type="text.xyz")
    win = ui.add_data_model(model)
    assert type(win.widget) is _qtw.QDefaultTextEdit
    register_widget("text.xyz", QCustomTextView)

    win2 = ui.add_data_model(model)
    assert type(win2.widget) is QCustomTextView

def test_register_folder(ui: MainWindow, sample_dir: Path):
    from himena.plugins import register_reader_provider

    def _read(fp: Path):
        files = list(fp.glob("*.*"))
        if files[0].name == "meta.txt":
            code, meta = files[1], files[0]
        elif files[1].name == "meta.txt":
            code, meta = files[0], files[1]
        else:
            raise ValueError("meta.txt not found")
        return WidgetDataModel(
            value=code.read_text(),
            type="text.with-meta",
            additional_data=meta,
        )

    @register_reader_provider
    def read_text_with_meta(path: Path):
        if path.is_file():
            return None
        files = list(path.glob("*.*"))
        if len(files) == 2 and "meta.txt" in [f.name for f in files]:
            return _read
        else:
            return None

    response_open = lambda: sample_dir / "folder"
    ui._instructions = ui._instructions.updated(
        file_dialog_response=response_open,
    )
    ui.exec_action("open-folder")

def test_clipboard(ui: MainWindow, sample_dir: Path):
    cmodel = ClipboardDataModel(value="XXX", type="text")
    ui.clipboard = cmodel

    ui.exec_action("paste-as-window")
    assert ui.current_window is not None
    assert ui.current_window.to_model().value == "XXX"

    sample_path = sample_dir / "text.txt"
    ui.read_file(sample_path)
    ui.exec_action("copy-path-to-clipboard")
    assert ui.clipboard.value == str(sample_path)
    ui.exec_action("copy-data-to-clipboard")
    assert ui.clipboard.value == sample_path.read_text()
    assert ui.clipboard.type == "text"

def test_tile_window(ui: MainWindow):
    ui.add_data("A", type="text")
    ui.add_data("B", type="text")
    ui.tabs[0].tile_windows()
    ui.add_data("C", type="text")
    ui.tabs[0].tile_windows()
    ui.add_data("D", type="text")
    ui.tabs[0].tile_windows()
    ui.add_data("E", type="text")
    ui.tabs[0].tile_windows()
    ui.add_data("F", type="text")
    ui.tabs[0].tile_windows()
    ui.add_data("G", type="text")
    ui.tabs[0].tile_windows()
    ui.add_data("H", type="text")
    ui.tabs[0].tile_windows()

def test_move_window(ui: MainWindow):
    tab0 = ui.add_tab()
    tab1 = ui.add_tab()
    win = tab0.add_data_model(WidgetDataModel(value="A", type="text"))
    ui.move_window(win, 1)
    assert win not in tab0
    assert win in tab1
    assert tab1[0]._identifier == win._identifier

def test_child_window(ui: MainWindow):
    win = ui.add_data("A", type="text")
    text_edit = QtW.QTextEdit()
    child = win.add_child(text_edit, title="Child")
    assert len(ui.tabs.current()) == 2
    del ui.tabs.current()[0]
    assert len(ui.tabs.current()) == 0
    assert not win.is_alive
    assert not child.is_alive
