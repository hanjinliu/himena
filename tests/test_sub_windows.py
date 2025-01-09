from pathlib import Path
import pytest
from pytestqt.qtbot import QtBot
from tempfile import TemporaryDirectory
from qtpy import QtWidgets as QtW
from himena import MainWindow, anchor
from himena._descriptors import NoNeedToSave, SaveToNewPath, SaveToPath
from himena.workflow import CommandExecution, LocalReaderMethod, ProgrammaticMethod
from himena.types import ClipboardDataModel, WidgetDataModel, WindowRect
from himena.qt import register_widget_class, MainWindowQt
from himena_builtins.qt import widgets as _qtw
import himena._providers

def test_new_window(himena_ui: MainWindow):
    himena_ui.show()
    assert len(himena_ui.tabs) == 0
    with TemporaryDirectory() as tmp:
        path = Path(tmp) / "test.txt"
        path.write_text("Hello, World!")
        himena_ui.read_file(path)
    assert len(himena_ui.tabs) == 1
    assert len(himena_ui.tabs[0]) == 1
    with TemporaryDirectory() as tmp:
        path = Path(tmp) / "test.txt"
        path.write_text("Hello, World! 2")
        himena_ui.read_file(path)
    assert len(himena_ui.tabs) == 1
    assert len(himena_ui.tabs[0]) == 2
    himena_ui.add_tab("New tab")
    assert len(himena_ui.tabs) == 2
    assert len(himena_ui.tabs.current()) == 0
    assert himena_ui.tabs.current().title == "New tab"

def test_builtin_commands(himena_ui: MainWindow):
    himena_ui.show()
    himena_ui.exec_action("new-tab")
    assert len(himena_ui.tabs) == 1
    assert len(himena_ui.tabs[0]) == 0
    himena_ui.exec_action("builtins:console")
    himena_ui.exec_action("builtins:file-explorer")
    himena_ui.exec_action("builtins:output")
    himena_ui.exec_action("builtins:new-text")
    assert len(himena_ui.tabs[0]) == 1
    himena_ui.exec_action("builtins:seaborn-sample:iris")
    himena_ui.exec_action("quit")

def test_io_commands(himena_ui: MainWindow, tmpdir, sample_dir: Path):
    response_open = lambda: [sample_dir / "text.txt"]
    response_save = lambda: Path(tmpdir) / "text_out.txt"
    himena_ui._instructions = himena_ui._instructions.updated(file_dialog_response=response_open)
    himena_ui.exec_action("open-file")
    assert isinstance(himena_ui.current_window.save_behavior, SaveToPath)
    last = himena_ui.current_window._widget_workflow.last()
    assert isinstance(last, LocalReaderMethod)
    assert last.output_model_type == "text"
    assert last.path == response_open()[0]

    himena_ui.add_object("Hello", type="text")
    assert isinstance(himena_ui.current_window.save_behavior, SaveToNewPath)
    assert isinstance(meth := himena_ui.current_window._widget_workflow.last(), ProgrammaticMethod)
    assert meth.output_model_type == "text"
    himena_ui._instructions = himena_ui._instructions.updated(file_dialog_response=response_save)
    himena_ui.exec_action("save")
    assert isinstance(himena_ui.current_window.save_behavior, SaveToPath)
    assert himena_ui.current_window.save_behavior.path == response_save()
    assert isinstance(himena_ui.current_window._widget_workflow.last(), ProgrammaticMethod)
    himena_ui.exec_action("save-as")

    # session
    response_session = lambda: Path(tmpdir) / "a.session.yaml"
    himena_ui._instructions = himena_ui._instructions.updated(file_dialog_response=response_session)
    himena_ui.exec_action("save-session")
    himena_ui.exec_action("load-session")

    himena_ui.exec_action("save-tab-session")

    response_open = lambda: sample_dir / "table.csv"
    himena_ui._instructions = himena_ui._instructions.updated(file_dialog_response=response_open)
    store = himena._providers.ReaderProviderStore.instance()
    param = store.get(response_open(), min_priority=-500)[2]
    himena_ui.exec_action("open-file-using", with_params={"reader": param})
    assert isinstance(himena_ui.current_window.save_behavior, SaveToPath)
    last = himena_ui.current_window._widget_workflow.last()
    assert isinstance(last, LocalReaderMethod)
    assert last.path == response_open()
    assert param.plugin is not None
    assert last.plugin == param.plugin.to_str()

def test_window_commands(himena_ui: MainWindowQt, sample_dir: Path):
    himena_ui.exec_action("show-command-palette")
    himena_ui.read_file(sample_dir / "text.txt")
    assert len(himena_ui.tabs) == 1
    assert len(himena_ui.tabs[0]) == 1
    himena_ui._backend_main_window.setFocus()
    himena_ui.exec_action("open-recent")
    himena_ui._backend_main_window.setFocus()

    himena_ui.exec_action("duplicate-window")
    himena_ui.exec_action("duplicate-window")
    assert len(himena_ui.tabs[0]) == 3
    himena_ui.exec_action("rename-window")

    # anchor
    himena_ui.exec_action("anchor-window-top-left")
    himena_ui.exec_action("anchor-window-top-right")
    himena_ui.exec_action("anchor-window-bottom-left")
    himena_ui.exec_action("anchor-window-bottom-right")
    himena_ui.exec_action("unset-anchor")

    # zoom
    himena_ui.exec_action("window-expand")
    himena_ui.exec_action("window-shrink")

    # align
    himena_ui.exec_action("align-window-left")
    himena_ui.exec_action("align-window-right")
    himena_ui.exec_action("align-window-top")
    himena_ui.exec_action("align-window-bottom")
    himena_ui.exec_action("align-window-center")

    # state
    himena_ui.exec_action("minimize-window")
    himena_ui.exec_action("maximize-window")
    himena_ui.exec_action("toggle-full-screen")
    himena_ui.exec_action("toggle-full-screen")
    himena_ui.exec_action("close-window")
    himena_ui.exec_action("show-command-palette")
    himena_ui.exec_action("new")

    himena_ui.read_file(sample_dir / "text.txt")
    assert len(himena_ui.tabs) == 1
    himena_ui.exec_action("full-screen-in-new-tab")
    assert len(himena_ui.tabs) == 2
    assert himena_ui.tabs.current_index == 1

def test_screenshot_commands(himena_ui: MainWindow, sample_dir: Path, tmpdir):
    himena_ui.read_file(sample_dir / "text.txt")

    # copy
    himena_ui.clipboard = ClipboardDataModel(text="")  # just for initialization
    himena_ui.exec_action("copy-screenshot")
    assert himena_ui.clipboard.image is not None
    himena_ui.clipboard = ClipboardDataModel(text="")  # just for initialization
    himena_ui.exec_action("copy-screenshot-area")
    assert himena_ui.clipboard.image is not None
    himena_ui.clipboard = ClipboardDataModel(text="")  # just for initialization
    himena_ui.exec_action("copy-screenshot-window")
    assert himena_ui.clipboard.image is not None

    # save
    himena_ui._instructions = himena_ui._instructions.updated(
        file_dialog_response=lambda: Path(tmpdir) / "screenshot.png"
    )
    himena_ui.exec_action("save-screenshot")
    himena_ui.exec_action("save-screenshot-area")
    himena_ui.exec_action("save-screenshot-window")
    assert Path(tmpdir).joinpath("screenshot.png").exists()

def test_view_menu_commands(himena_ui: MainWindow, sample_dir: Path):
    himena_ui.exec_action("new-tab")
    himena_ui.exec_action("close-tab")
    himena_ui.exec_action("new-tab")
    himena_ui.read_file(sample_dir / "text.txt")
    assert himena_ui.tabs.current().current_index == 0
    himena_ui.read_file(sample_dir / "text.txt")
    assert himena_ui.tabs.current().current_index == 1
    himena_ui.exec_action("new-tab")
    himena_ui.read_file(sample_dir / "text.txt")
    assert himena_ui.tabs.current_index == 1
    himena_ui.exec_action("goto-last-tab")
    assert himena_ui.tabs.current_index == 0
    assert len(himena_ui.tabs.current()) == 2
    assert himena_ui.tabs.current()[0].state == "normal"
    assert himena_ui.tabs.current()[1].state == "normal"
    himena_ui.exec_action("minimize-other-windows")
    assert himena_ui.tabs.current()[0].state == "min"
    assert himena_ui.tabs.current()[1].state == "normal"
    himena_ui.exec_action("show-all-windows")
    assert himena_ui.tabs.current()[0].state == "normal"
    assert himena_ui.tabs.current()[1].state == "normal"
    himena_ui.exec_action("close-all-windows")
    assert len(himena_ui.tabs.current()) == 0

    # close tab with unsaved
    win0 = himena_ui.read_file(sample_dir / "text.txt")
    win0.widget.set_modified(True)
    win1 = himena_ui.read_file(sample_dir / "table.csv")
    win1.widget.set_modified(True)
    himena_ui.read_file(sample_dir / "text.txt")
    himena_ui.exec_action("close-tab")

def test_custom_widget(himena_ui: MainWindow):
    from qtpy.QtWidgets import QLabel

    himena_ui.show()
    label = QLabel("Custom widget test")
    widget = himena_ui.add_widget(label)
    assert len(himena_ui.tabs) == 1
    assert len(himena_ui.tabs[0]) == 1
    widget.title = "New title"
    assert widget.title == "New title"
    widget.rect = WindowRect(10, 20, 100, 200)
    assert widget.rect == WindowRect(10, 20, 100, 200)
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

def test_custom_dock_widget(himena_ui: MainWindow):
    from qtpy.QtWidgets import QLabel

    himena_ui.show()
    widget = QLabel("Dock widget test")
    dock = himena_ui.add_dock_widget(widget)
    assert himena_ui.dock_widgets.len()
    assert dock.visible
    dock.visible = False
    assert not dock.visible
    dock.title = "New title"
    assert dock.title == "New title"

def test_fallback_widget(himena_ui: MainWindow):
    from himena.qt.registry._widgets import QFallbackWidget

    model = WidgetDataModel(value=object(), type="XYZ")
    with pytest.warns(RuntimeWarning):  # no widget class is registered for "XYZ"
        win = himena_ui.add_data_model(model)
    assert isinstance(win.widget, QFallbackWidget)

def test_register_widget(himena_ui: MainWindow):
    from qtpy.QtWidgets import QLabel

    class QCustomTextView(QLabel):
        def update_model(self, model: WidgetDataModel):
            return self.setText(model.value)

    model = WidgetDataModel(value="abc", type="text.xyz")
    win = himena_ui.add_data_model(model)
    assert type(win.widget) is _qtw.QTextEdit
    register_widget_class("text.xyz", QCustomTextView)

    win2 = himena_ui.add_data_model(model)
    assert type(win2.widget) is QCustomTextView

def test_register_folder(himena_ui: MainWindow, sample_dir: Path):
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
            metadata=meta,
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
    himena_ui._instructions = himena_ui._instructions.updated(
        file_dialog_response=response_open,
    )
    himena_ui.exec_action("open-folder")
    assert himena_ui.tabs.current_index == 0
    assert himena_ui.tabs.current().len() == 1

def test_clipboard(himena_ui: MainWindow, sample_dir: Path, qtbot: QtBot):
    qtbot.addWidget(himena_ui._backend_main_window)
    cmodel = ClipboardDataModel(text="XXX")
    himena_ui.clipboard = cmodel

    himena_ui.exec_action("paste-as-window")
    assert himena_ui.current_window is not None
    assert himena_ui.current_window.to_model().value == "XXX"

    sample_path = sample_dir / "text.txt"
    himena_ui.read_file(sample_path)
    QtW.QApplication.processEvents()
    himena_ui.exec_action("copy-path-to-clipboard")
    QtW.QApplication.processEvents()
    assert himena_ui.clipboard.text == str(sample_path)
    himena_ui.exec_action("copy-data-to-clipboard")
    assert himena_ui.clipboard.text == sample_path.read_text()

def test_tile_window(himena_ui: MainWindow):
    himena_ui.add_object("A", type="text")
    himena_ui.add_object("B", type="text")
    himena_ui.tabs[0].tile_windows()
    himena_ui.add_object("C", type="text")
    himena_ui.tabs[0].tile_windows()
    himena_ui.add_object("D", type="text")
    himena_ui.tabs[0].tile_windows()
    himena_ui.add_object("E", type="text")
    himena_ui.tabs[0].tile_windows()
    himena_ui.add_object("F", type="text")
    himena_ui.tabs[0].tile_windows()
    himena_ui.add_object("G", type="text")
    himena_ui.tabs[0].tile_windows()
    himena_ui.add_object("H", type="text")
    himena_ui.tabs[0].tile_windows()

def test_move_window(himena_ui: MainWindow):
    tab0 = himena_ui.add_tab()
    tab1 = himena_ui.add_tab()
    win = tab0.add_data_model(WidgetDataModel(value="A", type="text"))
    himena_ui.move_window(win, 1)
    assert win not in tab0
    assert win in tab1
    assert tab1[0]._identifier == win._identifier

def test_child_window(himena_ui: MainWindow):
    win = himena_ui.add_object("A", type="text")
    text_edit = QtW.QTextEdit()
    child = win.add_child(text_edit, title="Child")
    assert len(himena_ui.tabs.current()) == 2
    del himena_ui.tabs.current()[0]
    assert len(himena_ui.tabs.current()) == 0
    assert not win.is_alive
    assert not child.is_alive

def test_save_behavior(himena_ui: MainWindow, tmpdir):
    himena_ui.exec_action("builtins:new-text")
    win = himena_ui.current_window
    assert win is not None
    assert not win._need_ask_save_before_close()

    himena_ui.exec_action("duplicate-window")
    win2 = himena_ui.current_window
    assert not win2._need_ask_save_before_close()
    assert isinstance(win2._widget_workflow.last(), CommandExecution)
    # special case for duplicate-window
    assert isinstance(win2.save_behavior, NoNeedToSave)

    response_save = lambda: Path(tmpdir) / "text_out.txt"
    himena_ui._instructions = himena_ui._instructions.updated(file_dialog_response=response_save)
    himena_ui.exec_action("save-as")
    win3 = himena_ui.current_window
    assert not win3._need_ask_save_before_close()
    assert isinstance(win3._widget_workflow.last(), CommandExecution)
    assert isinstance(win3.save_behavior, SaveToPath)

    himena_ui.current_window = win3
    himena_ui.exec_action("open-in:builtins:QTextEdit")
    win3 = himena_ui.current_window
    assert isinstance(win3.save_behavior, NoNeedToSave)

# NOTE: cannot pickle local object. Must be defined here.
class MyObj:
    def __init__(self, value):
        self.value = value

def _set_response(himena_ui: MainWindow, path):
    assert isinstance(path, Path)
    response = lambda: path
    himena_ui._instructions = himena_ui._instructions.updated(file_dialog_response=response, confirm=False)

def test_dont_use_pickle(himena_ui: MainWindow, tmpdir):
    tmpdir = Path(tmpdir)
    data = MyObj(124)
    with pytest.warns(RuntimeWarning):  # no widget class is registered for "myobj"
        himena_ui.add_object(data, type="myobj")
    _set_response(himena_ui, tmpdir / "test.txt")
    with pytest.raises(ValueError):
        himena_ui.exec_action("save")
    _set_response(himena_ui, tmpdir / "test.pickle")
    himena_ui.exec_action("save")
    assert (tmpdir / "test.pickle").exists()
    _set_response(himena_ui, tmpdir / "test.pickle")
    with pytest.warns(RuntimeWarning):  # no widget class is registered for "any"
        himena_ui.exec_action("open-file")
    model = himena_ui.current_window.to_model()
    assert isinstance(model.value, MyObj)
    assert model.value.value == 124

def test_open_and_save_files(himena_ui: MainWindow, tmpdir, sample_dir: Path):
    himena_ui.show()
    tmpdir = Path(tmpdir)
    _set_response(himena_ui, sample_dir / "ipynb.ipynb")
    himena_ui.exec_action("open-file")
    _set_response(himena_ui, tmpdir / "ipynb.ipynb")
    himena_ui.exec_action("save-as")

    _set_response(himena_ui, sample_dir / "excel.xlsx")
    himena_ui.exec_action("open-file")
    _set_response(himena_ui, tmpdir / "excel.xlsx")
    himena_ui.exec_action("save-as")

    _set_response(himena_ui, sample_dir / "array.npy")
    himena_ui.exec_action("open-file")
    _set_response(himena_ui, tmpdir / "array.npy")
    himena_ui.exec_action("save-as")

    _set_response(himena_ui, sample_dir / "array_structured.npy")
    himena_ui.exec_action("open-file")
    _set_response(himena_ui, tmpdir / "array_structured.npy")
    himena_ui.exec_action("save-as")

    himena_ui.exec_action("builtins:stack-models", with_params={"models": [], "pattern": ".*"})
    _set_response(himena_ui, tmpdir / "stack.zip")
    himena_ui.exec_action("save-as")
    himena_ui.exec_action("open-file")

    himena_ui.add_object({"x": [1, 2, 3], "y": [4.2, 5.3, -1.5]}, type="dataframe")
    himena_ui.add_object(
        {"x": [1, 2, 3], "y": [4.2, 5.3, -1.5], "z": [2.2, 1.1, 2.2]},
        type="dataframe.plot",
    )
