from pathlib import Path
import sys
import pytest
from pytestqt.qtbot import QtBot
from qtpy import QtWidgets as QtW
import numpy as np
from numpy.testing import assert_equal
import polars as pl

from himena import MainWindow, anchor
from himena._descriptors import NoNeedToSave, SaveToNewPath, SaveToPath
from himena.consts import StandardType
from himena.core import create_model
from himena.style import Theme
from himena.workflow import CommandExecution, LocalReaderMethod, ProgrammaticMethod
from himena.types import ClipboardDataModel, DragDataModel, WidgetDataModel, WindowRect
from himena.testing import file_dialog_response
from himena.qt import register_widget_class, MainWindowQt
from himena.testing import choose_one_dialog_response
from himena_builtins.qt.text import QTextEdit
import himena._providers

def test_new_window(make_himena_ui, backend: str, tmpdir):
    himena_ui: MainWindow = make_himena_ui(backend)
    himena_ui.show()
    tmpdir = Path(tmpdir)
    path = tmpdir / "test.txt"
    assert len(himena_ui.tabs) == 0
    assert len(himena_ui.windows_for_type(StandardType.TEXT)) == 0
    path.write_text("Hello, World!")
    himena_ui.read_file(path)
    assert len(himena_ui.tabs) == 1
    assert len(himena_ui.tabs[0]) == 1
    assert himena_ui.tabs[0][-1].is_editable
    himena_ui.exec_action("window-toggle-editable")
    assert not himena_ui.tabs[0][-1].is_editable
    path.write_text("Hello, World! 2")
    himena_ui.read_file(path)
    assert len(himena_ui.tabs) == 1
    assert len(himena_ui.tabs[0]) == 2

    assert len(himena_ui.windows_for_type(StandardType.TEXT)) == 2
    assert himena_ui.windows_for_type((StandardType.TABLE, StandardType.ARRAY)) == []

    himena_ui.add_tab("New tab")
    assert len(himena_ui.tabs) == 2
    assert len(himena_ui.tabs.current()) == 0
    assert himena_ui.tabs.current().title == "New tab"
    assert himena_ui.tabs.current().is_alive
    himena_ui.tabs._get_by_hash(himena_ui.tabs[0])
    result = himena_ui.tabs[0].read_files_async([path])
    result.result()
    assert himena_ui.tabs[0][-1].to_model().value == "Hello, World! 2"

    if backend == "qt":
        class CustomWidget:
            pass

        with pytest.raises(TypeError):
            himena_ui.add_widget(CustomWidget())

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
    config = {"format": "%(levelname)s:%(message)s", "date_format": "%Y-%m-%d %H:%M:%S"}
    himena_ui.app_profile.update_plugin_config("builtins:output", **config)
    himena_ui.exec_action("builtins:new-table")
    himena_ui.exec_action("builtins:new-excel")
    himena_ui.exec_action("builtins:new-text-python")
    with choose_one_dialog_response(himena_ui, "Copy"):
        himena_ui.exec_action("show-about")
    himena_ui.exec_action("quit")


def test_io_commands(himena_ui: MainWindow, tmpdir, sample_dir: Path):
    open_path = [sample_dir / "text.txt"]

    with file_dialog_response(himena_ui, open_path):
        himena_ui.exec_action("open-file")
    assert isinstance(himena_ui.current_window.save_behavior, SaveToPath)
    last = himena_ui.current_window._widget_workflow.last()
    assert isinstance(last, LocalReaderMethod)
    assert last.output_model_type == "text"
    assert last.path == open_path[0]

    himena_ui.add_object("Hello", type="text")
    assert isinstance(himena_ui.current_window.save_behavior, SaveToNewPath)
    assert isinstance(meth := himena_ui.current_window._widget_workflow.last(), ProgrammaticMethod)
    assert meth.output_model_type == "text"
    with file_dialog_response(himena_ui, Path(tmpdir) / "text_out.txt") as save_path:
        himena_ui.exec_action("save")
        assert save_path.exists()
        save_path.unlink()
        assert isinstance(himena_ui.current_window.save_behavior, SaveToPath)
        assert himena_ui.current_window.save_behavior.path == save_path
        assert isinstance(himena_ui.current_window._widget_workflow.last(), ProgrammaticMethod)
        himena_ui.exec_action("save-as")
        assert save_path.exists()

    # saving no extension
    with file_dialog_response(himena_ui, Path(tmpdir) / "noext") as save_path:
        himena_ui.exec_action("save-as")
        assert save_path.exists()

    # session
    with file_dialog_response(himena_ui, Path(tmpdir) / "a.session.zip") as session_path:
        himena_ui.exec_action("save-session", with_params={"save_path": session_path})
        himena_ui.exec_action("load-session")
        himena_ui.exec_action("save-tab-session")

    with file_dialog_response(himena_ui, sample_dir / "table.csv") as open_path:
        store = himena._providers.ReaderStore.instance()
        param = store.get(open_path, min_priority=-500)[2]
        himena_ui.exec_action("open-file-with", with_params={"reader": param})
        assert isinstance(himena_ui.current_window.save_behavior, SaveToPath)
        last = himena_ui.current_window._widget_workflow.last()
        assert isinstance(last, LocalReaderMethod)
        assert last.path == open_path
        assert param.plugin is not None
        assert last.plugin == param.plugin.to_str()

    # backup
    with file_dialog_response(himena_ui, sample_dir / "text.txt~") as open_path:
        himena_ui.exec_action("open-file")
        assert himena_ui.current_window.to_model().type == StandardType.TEXT
        assert himena_ui.current_window.to_model().value == "ab\n"
    with file_dialog_response(himena_ui, Path(tmpdir) / "out.log~") as save_path:
        himena_ui.exec_action("save")

    # test adding object directly
    himena_ui.add_object("ABC")
    himena_ui.add_object(np.arange(4))
    himena_ui.add_object(np.array([[1, 2], [3, 4]], dtype=np.dtypes.StringDType()))
    himena_ui.add_object(pl.DataFrame({"x": [1, 2, 3], "y": [4.2, 5.3, -1.5]}))
    himena_ui.current_model.write_to_directory(tmpdir)
    with file_dialog_response(
        himena_ui,
        [sample_dir / "text.txt", sample_dir / "text.txt~"]
    ) as open_path:
        himena_ui.exec_action("open-file-group")

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
    himena_ui.exec_action("show-whats-this")
    assert himena_ui.current_window.widget.__doc__
    himena_ui.exec_action("full-screen-in-new-tab")
    assert len(himena_ui.tabs) == 2
    assert himena_ui.tabs.current_index == 1

    himena_ui._backend_main_window._tab_renamed(0, "renamed-tab")
    himena_ui._backend_main_window._set_tab_name(0, "renamed-tab-2")
    himena_ui._backend_main_window._update_widget_theme(Theme.from_global("light-green"))
    himena_ui._backend_main_window._update_widget_theme(Theme.from_global("dark-green"))

def test_screenshot_commands(himena_ui: MainWindow, sample_dir: Path, tmpdir):
    himena_ui.read_file(sample_dir / "text.txt")

    # copy
    himena_ui.clipboard = ClipboardDataModel(text="")  # just for initialization
    QtW.QApplication.processEvents()
    himena_ui.exec_action("copy-screenshot")
    QtW.QApplication.processEvents()
    assert himena_ui.clipboard.image is not None
    himena_ui.clipboard = ClipboardDataModel(text="")  # just for initialization
    QtW.QApplication.processEvents()
    himena_ui.exec_action("copy-screenshot-area")
    QtW.QApplication.processEvents()
    assert himena_ui.clipboard.image is not None
    himena_ui.clipboard = ClipboardDataModel(text="")  # just for initialization
    QtW.QApplication.processEvents()
    himena_ui.exec_action("copy-screenshot-window")
    QtW.QApplication.processEvents()
    assert himena_ui.clipboard.image is not None

    # save
    with file_dialog_response(himena_ui, Path(tmpdir) / "screenshot.png") as save_path:
        himena_ui.exec_action("save-screenshot")
        assert save_path.exists()
        save_path.unlink()
        himena_ui.exec_action("save-screenshot-area")
        assert save_path.exists()
        save_path.unlink()
        himena_ui.exec_action("save-screenshot-window")
        assert save_path.exists()
        save_path.unlink()

def test_view_menu_commands(himena_ui: MainWindowQt, sample_dir: Path):
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
    himena_ui.add_tab().add_data_model(create_model("a", type="text", title="ABC2"))
    himena_ui.exec_action("merge-tabs", with_params={"names": himena_ui.tabs.names})
    assert len(himena_ui.tabs) == 1
    himena_ui.exec_action("tile-windows")
    himena_ui.add_tab().add_data_model(create_model("a", type="text", title="ABC1"))
    himena_ui.exec_action("collect-windows", with_params={"pattern": "ABC*"})
    himena_ui._backend_main_window._tab_widget._tabbar._prep_drag(0)
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
    assert type(win.widget) is QTextEdit
    register_widget_class("text.xyz", QCustomTextView)

    win2 = himena_ui.add_data_model(model)
    assert type(win2.widget) is QCustomTextView

    # test multiple registration
    register_widget_class("text.abcde", QCustomTextView)

def test_register_folder(himena_ui: MainWindow, sample_dir: Path):
    from himena.plugins import register_reader_plugin

    @register_reader_plugin
    def read_text_with_meta(path: Path):
        if path.is_file():
            raise ValueError("Not a folder")
        files = list(path.glob("*.*"))
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

    @read_text_with_meta.define_matcher
    def _(path: Path):
        if path.is_file():
            return None
        files = list(path.glob("*.*"))
        if len(files) == 2 and "meta.txt" in [f.name for f in files]:
            return "text.with-meta"
        else:
            return None

    with file_dialog_response(himena_ui, sample_dir / "folder"):
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
    QtW.QApplication.processEvents()
    himena_ui.exec_action("copy-data-to-clipboard")
    QtW.QApplication.processEvents()
    assert himena_ui.clipboard.text == sample_path.read_text()
    himena_ui.add_object(np.zeros((6, 5, 3)), type=StandardType.IMAGE)
    QtW.QApplication.processEvents()
    himena_ui.exec_action("copy-data-to-clipboard")
    QtW.QApplication.processEvents()
    img = np.zeros((6, 5, 4), dtype=np.uint8)
    img[..., 3] = 255
    assert_equal(himena_ui.clipboard.image, img)
    himena_ui.add_object("<b>a</b>", type=StandardType.HTML)
    QtW.QApplication.processEvents()
    himena_ui.exec_action("copy-data-to-clipboard")
    QtW.QApplication.processEvents()
    assert himena_ui.clipboard.text == "a"

def test_tile_window(make_himena_ui, backend: str):
    himena_ui: MainWindow = make_himena_ui(backend)
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

def test_move_window(make_himena_ui, backend: str):
    himena_ui: MainWindow = make_himena_ui(backend)
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

    with file_dialog_response(himena_ui, Path(tmpdir) / "test.txt") as response_save:
        himena_ui.exec_action("save-as")
    win3 = himena_ui.current_window
    assert not win3._need_ask_save_before_close()
    assert isinstance(win3._widget_workflow.last(), CommandExecution)
    assert isinstance(win3.save_behavior, SaveToPath)

    himena_ui.current_window = win3
    himena_ui.exec_action("open-in:builtins:QTextEdit:text")
    win3 = himena_ui.current_window
    assert isinstance(win3.save_behavior, NoNeedToSave)

# NOTE: cannot pickle local object. Must be defined here.
class MyObj:
    def __init__(self, value):
        self.value = value


def test_dont_use_pickle(himena_ui: MainWindow, tmpdir):
    tmpdir = Path(tmpdir)
    data = MyObj(124)
    with pytest.warns(RuntimeWarning):  # no widget class is registered for "myobj"
        himena_ui.add_object(data, type="myobj")
    with file_dialog_response(himena_ui, tmpdir / "test.txt"):
        with pytest.raises(ValueError):  # No writer function available for "myobj"
            himena_ui.exec_action("save")
    with file_dialog_response(himena_ui, tmpdir / "test.pickle"):
        himena_ui.exec_action("save")
        assert (tmpdir / "test.pickle").exists()
        with pytest.warns(RuntimeWarning):  # no widget class is registered for "any"
            himena_ui.exec_action("open-file")
    model = himena_ui.current_window.to_model()
    assert isinstance(model.value, MyObj)
    assert model.value.value == 124


def test_open_and_save_files(himena_ui: MainWindow, tmpdir, sample_dir: Path):
    himena_ui.show()
    tmpdir = Path(tmpdir)
    with file_dialog_response(himena_ui, sample_dir / "ipynb.ipynb"):
        himena_ui.exec_action("open-file")

    with file_dialog_response(himena_ui, sample_dir / "excel.xlsx"):
        himena_ui.exec_action("open-file")

    himena_ui.exec_action("builtins:models:stack-models", with_params={"models": [], "pattern": ".*"})
    with file_dialog_response(himena_ui, tmpdir / "stack.zip"):
        himena_ui.exec_action("save-as")
        himena_ui.exec_action("open-file")

    himena_ui.add_object({"x": [1, 2, 3], "y": [4.2, 5.3, -1.5]}, type="dataframe")
    himena_ui.add_object(
        {"x": [1, 2, 3], "y": [4.2, 5.3, -1.5], "z": [2.2, 1.1, 2.2]},
        type="dataframe.plot",
    )

    del himena_ui.tabs[0][0]
    himena_ui.exec_action("open-last-closed-window")
    assert himena_ui.tabs[0][-1].model_type() == StandardType.IPYNB
    assert isinstance(himena_ui.tabs[0][-1].to_model().workflow.last(), LocalReaderMethod)

    image_value = np.arange(5 * 20 * 15 * 3, dtype=np.uint8).reshape(5, 20, 15, 3)
    himena_ui.add_object(image_value, type="array.image")
    save_path = tmpdir / "array_image.gif"
    with file_dialog_response(himena_ui, save_path):
        himena_ui.exec_action("save-as")
        himena_ui.exec_action("open-file")
        assert_equal(himena_ui.current_window.to_model().value, image_value)


def test_reading_file_group(himena_ui: MainWindow, sample_dir: Path):
    tab0 = himena_ui.add_tab()
    win = tab0.read_file(
        [
            sample_dir / "text.txt",
            sample_dir / "json.json",
            sample_dir / "table.csv",
        ]
    )
    assert win.model_type() == StandardType.MODELS

def test_watch_file(himena_ui: MainWindow, tmpdir):
    filepath = Path(tmpdir) / "test.txt"
    filepath.write_text("x")
    with file_dialog_response(himena_ui, filepath):
        from himena.io_utils import get_readers
        tuples = get_readers(filepath)
        himena_ui.exec_action("watch-file-using", with_params={"reader": tuples[0]})
        win = himena_ui.current_window
        assert win.model_type() == StandardType.TEXT
        assert not win.is_editable
        assert win.to_model().value == "x"
        filepath.write_text("yy")
        # need enough time of processing
        for _ in range(5):
            QtW.QApplication.processEvents()
        if sys.platform != "darwin":  # this sometimes fails in mac
            assert win.to_model().value == "yy"

def test_drop_event(himena_ui: MainWindow):
    win = himena_ui.add_object(
        {"A": [[1, 2], [3, 4]]}, type=StandardType.EXCEL
    )
    win._process_drop_event(
        DragDataModel(
            getter=create_model({"B": [[3, 2]]}, type=StandardType.EXCEL, add_empty_workflow=True),
        )
    )
    win._ask_save_before_close = True
    with choose_one_dialog_response(himena_ui, "Cancel"):
        win._close_me(himena_ui, confirm=True)
    with choose_one_dialog_response(himena_ui, "Don't save"):
        win._close_me(himena_ui, confirm=True)
