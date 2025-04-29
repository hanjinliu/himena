from typing import Callable
from pathlib import Path
from unittest.mock import MagicMock

from himena import MainWindow, anchor
from himena.consts import StandardType
from himena.plugins import register_reader_plugin
from himena.types import WidgetDataModel, WindowRect
from himena.standards.model_meta import DataFrameMeta, ImageMeta, TextMeta
from himena.standards.roi import RectangleRoi
from himena_builtins.io import read_text
from himena_builtins.qt.text import QTextEdit, QRichTextEdit
from himena_builtins.qt.image import QImageView
from himena_builtins.qt.dataframe import QDataFrameView
from himena_builtins.qt.table import QSpreadsheet

def test_type_map_and_session(tmpdir, himena_ui: MainWindow, sample_dir):
    tab0 = himena_ui.add_tab()
    tab0.read_file(sample_dir / "text.txt").update(rect=(30, 40, 120, 150))
    assert type(tab0.current().widget) is QTextEdit
    tab0.read_file(sample_dir / "json.json").update(rect=(150, 40, 250, 150), anchor="top-left")
    assert type(tab0.current().widget) is QTextEdit
    tab1 = himena_ui.add_tab()
    tab1.read_file(sample_dir / "image.png").update(rect=(30, 40, 160, 130), title="My Image")
    assert type(tab1.current().widget) is QImageView
    tab1.read_file(sample_dir / "html.html").update(rect=(80, 40, 160, 130), title="My HTML")
    assert type(tab1.current().widget) is QRichTextEdit

    session_path = Path(tmpdir) / "test.session.zip"
    himena_ui.save_session(session_path)
    himena_ui.clear()
    assert len(himena_ui.tabs) == 0
    himena_ui.load_session(session_path)
    assert len(himena_ui.tabs) == 2
    assert len(himena_ui.tabs[0]) == 2
    assert himena_ui.tabs[0][0].title == "text.txt"
    assert himena_ui.tabs[0][0].rect == WindowRect(30, 40, 120, 150)
    assert himena_ui.tabs[0][1].title == "json.json"
    assert himena_ui.tabs[0][1].rect == WindowRect(150, 40, 250, 150)
    assert isinstance(himena_ui.tabs[0][1].anchor, anchor.TopLeftConstAnchor)
    assert len(himena_ui.tabs[1]) == 2
    assert himena_ui.tabs[1][0].title == "My Image"
    assert himena_ui.tabs[1][0].rect == WindowRect(30, 40, 160, 130)
    assert himena_ui.tabs[1][1].title == "My HTML"
    assert himena_ui.tabs[1][1].rect == WindowRect(80, 40, 160, 130)

def test_session_with_calculation(
    tmpdir,
    make_himena_ui: Callable[..., MainWindow],
    sample_dir,
):
    himena_ui = make_himena_ui("mock")
    tab0 = himena_ui.add_tab()
    tab0.read_file(sample_dir / "image.png").update(rect=(30, 40, 160, 130), title="Im")
    himena_ui.exec_action("builtins:image:crop-image", with_params={"y": (1, 3), "x": (1, 3)})
    assert len(tab0) == 2
    shape_cropped = tab0[1].to_model().value.shape
    tab0[1].update(rect=(70, 20, 160, 130))
    tab0[1].update_metadata(ImageMeta(current_roi=RectangleRoi(x=1, y=1, width=1, height=1)))
    meta = tab0[1].to_model().metadata
    assert isinstance(meta, ImageMeta)
    assert isinstance(meta.current_roi, RectangleRoi)
    tab0[1].title = "cropped Im"
    session_path = Path(tmpdir) / "test.session.zip"
    himena_ui.exec_action(
        "save-session",
        with_params={
            "save_path": session_path,
            "allow_calculate": ["builtins:image:crop-image"]
        },
    )
    himena_ui.clear()
    himena_ui.load_session(session_path)
    tab0 = himena_ui.tabs[0]
    assert len(tab0) == 2
    assert tab0[0].title == "Im"
    assert tab0[0].rect == WindowRect(30, 40, 160, 130)
    assert tab0[1].title == "cropped Im"
    assert tab0[1].rect == WindowRect(70, 20, 160, 130)
    assert tab0[1].to_model().value.shape == shape_cropped
    meta = tab0[1].to_model().metadata
    assert isinstance(meta, ImageMeta)
    assert isinstance(roi := meta.current_roi, RectangleRoi)
    assert roi.x == 1
    assert roi.y == 1
    assert roi.width == 1
    assert roi.height == 1

def test_session_stand_alone(tmpdir, himena_ui: MainWindow, sample_dir):
    tab0 = himena_ui.add_tab()
    tab0.read_file(sample_dir / "image.png").update(rect=(30, 40, 160, 130), title="Im")
    himena_ui.exec_action("builtins:image:crop-image", with_params={"y": (1, 3), "x": (1, 3)})
    shape_cropped = tab0[1].to_model().value.shape
    tab0[1].update(rect=(70, 20, 160, 130))

    tab1 = himena_ui.add_tab()
    tab1.read_file(sample_dir / "text.txt")
    win = tab1.read_file(
        sample_dir / "table.csv",
        plugin="himena_builtins.io.read_as_pandas_dataframe",
    )
    assert isinstance(win.widget, QDataFrameView)
    win.widget.selection_model.set_ranges([(slice(1, 3), slice(1, 2))])
    session_path = Path(tmpdir) / "test.session.zip"
    himena_ui.save_session(session_path, save_copies=True)
    himena_ui.clear()
    himena_ui.load_session(session_path)
    tab0 = himena_ui.tabs[0]
    tab1 = himena_ui.tabs[1]
    assert len(tab0) == 2
    assert tab0[0].title == "Im"
    assert tab0[0].rect == WindowRect(30, 40, 160, 130)
    assert tab0[1].rect == WindowRect(70, 20, 160, 130)
    assert tab0[1].to_model().value.shape == shape_cropped
    assert tab1[1].model_type() == StandardType.DATAFRAME
    assert isinstance(meta := tab1[1].to_model().metadata, DataFrameMeta)
    assert meta.selections == [((1, 3), (1, 2))]

def test_session_window_input(himena_ui: MainWindow):
    from himena_builtins.tools.others import exec_workflow

    himena_ui.exec_action("builtins:seaborn-sample:iris")
    win = himena_ui.current_window
    assert isinstance(win.widget, QSpreadsheet)
    win.widget.array_update((1, 1), "10.4")
    himena_ui.exec_action(
        "builtins:plot:scatter",
        with_params={"x": ((0, 10), (0, 1)), "y": ((0, 10), (1, 2))},
    )
    himena_ui.exec_action("show-workflow-graph")
    exec_workflow(himena_ui.current_model)
    assert himena_ui.current_window.model_type() == StandardType.PLOT

def test_session_with_no_param_command(make_himena_ui: Callable[..., MainWindow], tmpdir):
    himena_ui = make_himena_ui("mock")
    himena_ui.exec_action("builtins:new-text")
    himena_ui.exec_action("builtins:general:show-statistics")
    himena_ui.save_session(
        Path(tmpdir) / "test.session.zip",
        allow_calculate=["builtins:new-text", "builtins:general:show-statistics"]
    )
    himena_ui.clear()
    himena_ui.load_session(Path(tmpdir) / "test.session.zip")
    assert len(himena_ui.tabs) == 1
    assert len(himena_ui.tabs[0]) == 2


def test_session_calculate_non_savable(make_himena_ui: Callable[..., MainWindow], tmpdir):
    himena_ui = make_himena_ui("mock")
    _command_id = "test:temp-func"

    @himena_ui.register_function(command_id=_command_id)
    def _temp_func(model: WidgetDataModel) -> WidgetDataModel:
        # convert a model to a non-savable object
        return WidgetDataModel(value=object(), type="unknown-object", metadata=model.metadata)

    himena_ui.exec_action("builtins:new-text")
    assert himena_ui.current_model.metadata is not None
    himena_ui.exec_action(_command_id)
    # this session will be saved, because the non-savable object will be calculated.
    himena_ui.save_session(
        Path(tmpdir) / "test.session.zip",
        allow_calculate=["test:temp-func"]
    )

    himena_ui.clear()
    himena_ui.load_session(Path(tmpdir) / "test.session.zip")
    assert len(himena_ui.tabs) == 1
    assert len(himena_ui.tabs[0]) == 2
    assert himena_ui.tabs[0][1].model_type() == "unknown-object"
    assert isinstance(himena_ui.tabs[0][1].to_model().metadata, TextMeta)

def test_session_calculate_call_count(
    make_himena_ui: Callable[..., MainWindow],
    tmpdir,
    sample_dir: Path,
):
    himena_ui = make_himena_ui("qt")
    mock0 = MagicMock()
    mock1 = MagicMock()
    mock2 = MagicMock()

    @register_reader_plugin
    def _test_reader(path: Path) -> WidgetDataModel:
        mock0(0)
        return read_text(path)

    @_test_reader.define_matcher
    def _matcher(path: Path):
        if path.suffix == ".csv":
            return StandardType.TABLE
        return None

    _command_id_1 = "test:temp-func-1"

    @himena_ui.register_function(command_id=_command_id_1)
    def _temp_func_1(model: WidgetDataModel) -> WidgetDataModel:
        mock1(0)
        return model.with_title_numbering()

    _command_id_2 = "test:temp-func-2"

    @himena_ui.register_function(command_id=_command_id_2)
    def _temp_func_2(model: WidgetDataModel) -> WidgetDataModel:
        mock2(0)
        return model.with_title_numbering()

    himena_ui.read_file(sample_dir / "table.csv")
    himena_ui.exec_action(_command_id_1)
    himena_ui.exec_action(_command_id_2)
    assert mock0.call_count == 1
    assert mock1.call_count == 1
    assert mock2.call_count == 1

    mock0.reset_mock()
    mock1.reset_mock()
    mock2.reset_mock()

    # save and load session
    session_path = Path(tmpdir) / "test.session.zip"
    himena_ui.save_session(session_path, allow_calculate=[_command_id_2])
    himena_ui.clear()
    mock0.assert_not_called()
    mock1.assert_not_called()
    mock2.assert_not_called()

    himena_ui.load_session(session_path)
    assert (mock0.call_count, mock1.call_count, mock2.call_count,) == (0, 0, 1)


def test_list_of_subwindows_input(
    make_himena_ui: Callable[..., MainWindow],
    tmpdir,
):
    tmpdir = Path(tmpdir)
    himena_ui = make_himena_ui("qt")
    himena_ui.exec_action("builtins:constant-array", with_params={"interpret_as_image": True, "shape": (3, 3), "value": 1})
    win0 = himena_ui.current_window
    himena_ui.exec_action("builtins:constant-array", with_params={"interpret_as_image": True, "shape": (3, 3), "value": 2})
    win1 = himena_ui.current_window
    himena_ui.exec_action("builtins:image:stack-images", with_params={"images": [win0, win1], "axis_name": "p"})
    himena_ui.exec_action(
        "save-session",
        with_params={
            "save_path": str(tmpdir / "test.session.zip"),
            "allow_calculate": ["builtins:image:stack-images"],
        }
    )
    himena_ui.clear()
    himena_ui.load_session(tmpdir / "test.session.zip")
    assert len(himena_ui.tabs) == 1
    assert len(himena_ui.tabs.current()) == 3

    himena_ui.exec_action(
        "save-session",
        with_params={
            "save_path": str(tmpdir / "test.session.zip"),
            "allow_calculate": ["builtins:constant-array", "builtins:image:stack-images"],
        }
    )
    himena_ui.clear()
    himena_ui.load_session(tmpdir / "test.session.zip")
    assert len(himena_ui.tabs) == 1
    assert len(himena_ui.tabs.current()) == 3
