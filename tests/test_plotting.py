import os
from pathlib import Path
from cmap import Color, Colormap
import numpy as np
import matplotlib.pyplot as plt

from himena.standards.model_meta import ArrayMeta
from himena.types import WidgetDataModel
from himena.widgets import MainWindow
import himena.standards.plotting as hplt
from himena_builtins.qt.plot import BACKEND_HIMENA
from himena_builtins.qt.plot._canvas import QMatplotlibCanvas

def _str_array(arr):
    return np.array(arr, dtype=np.dtypes.StringDType())

def test_direct_plot(himena_ui: MainWindow):
    assert os.environ["MPLBACKEND"] == BACKEND_HIMENA
    plt.switch_backend(BACKEND_HIMENA)
    tab = himena_ui.add_tab()
    plt.figure(figsize=(3, 3))
    assert len(tab) == 0
    plt.plot([0, 1, 2])
    plt.show()
    assert len(tab) == 1
    assert isinstance(tab[0].widget, QMatplotlibCanvas)

def test_scatter_plot_via_command(make_himena_ui, tmpdir):
    himena_ui: MainWindow = make_himena_ui("mock")
    win = himena_ui.add_object(
        _str_array(
            [["x", "y", "z"],
             [0, 4, 6],
             [1, 6, 10],
             [2, 5, 12]],
        ),
        type="table",
    )
    himena_ui.current_window  = win
    himena_ui.exec_action(
        "builtins:scatter-plot",
        with_params={
            "x": ((0, 99), (0, 1)),
            "y": ((0, 99), (1, 2)),
            "face": {"color": Color("red"), "hatch": "/"},
            "edge": {"color": Color("blue"), "width": 2.5, "style": "--"},
        }
    )
    himena_ui.current_window  = win
    himena_ui.exec_action(
        "builtins:scatter-plot",
        with_params={
            "x": ((0, 99), (0, 1)),
            "y": ((0, 99), (1, 3)),
            "face": {"color": Colormap("tab10"), "hatch": None},
            "edge": {"color": Color("black"), "width": 2, "style": None},
        }
    )
    path = Path(tmpdir) / "test.plot.json"
    himena_ui.current_window.write_model(path)
    himena_ui.read_file(path)

    win = himena_ui.add_object(
        _str_array(
            [["x", "y", "z"],
             [0, 4, 6],
             [1, 6, 10],
             [2, 5, 12]],
        ),
        type="table",
    )
    himena_ui.exec_action(
        "builtins:plot-3d:scatter-plot-3d",
        with_params={
            "x": ((0, 99), (0, 1)),
            "y": ((0, 99), (1, 2)),
            "z": ((0, 99), (2, 3)),
        }
    )
    win_3d = himena_ui.current_window
    path = Path(tmpdir) / "test.plot.json"
    himena_ui.current_window.write_model(path)
    himena_ui.read_file(path)
    himena_ui.exec_action("builtins:plot:plot-to-dataframe", with_params={"component": 0})
    himena_ui.exec_action("builtins:plot:plot-to-dataframe", with_params={"component": 0}, window_context=win_3d)

def test_scatter_plot_many_data_types(make_himena_ui):
    himena_ui: MainWindow = make_himena_ui("mock")
    himena_ui.add_data_model(
        WidgetDataModel(
            value=np.array([[1, 2], [2, 3], [3, 2]]),
            type="array",
            metadata=ArrayMeta(),
        )
    )
    himena_ui.exec_action(
        "builtins:scatter-plot",
        with_params={"x": ((0, 3), (0, 1)), "y": ((0, 3), (1, 2))},
    )
    himena_ui.add_object({"x": [1, 2, 3], "y": [2, 3, 2]}, type="dataframe")
    himena_ui.exec_action(
        "builtins:scatter-plot",
        with_params={"x": ((0, 3), (0, 1)), "y": ((0, 3), (1, 2))},
    )

def test_line_plot_via_command(make_himena_ui, tmpdir):
    himena_ui: MainWindow = make_himena_ui("mock")
    win = himena_ui.add_object(
        _str_array(
            [["x", "y", "z"],
             [0, 4, 6],
             [1, 6, 10],
             [2, 5, 12]],
        ),
        type="table",
    )
    himena_ui.current_window  = win
    himena_ui.exec_action(
        "builtins:line-plot",
        with_params={
            "x": ((0, 99), (0, 1)),
            "y": ((0, 99), (1, 2)),
            "edge": {"color": Color("blue"), "width": 2.5, "style": "--"},
        }
    )
    himena_ui.current_window  = win
    himena_ui.exec_action(
        "builtins:line-plot",
        with_params={
            "x": ((0, 99), (0, 1)),
            "y": ((0, 99), (1, 3)),
            "edge": {"color": Color("black"), "width": 2, "style": None},
        }
    )
    path = Path(tmpdir) / "test.plot.json"
    himena_ui.current_window.write_model(path)
    himena_ui.read_file(path)

    win = himena_ui.add_object(
        _str_array(
            [["x", "y", "z"],
             [0, 4, 6],
             [1, 6, 10],
             [2, 5, 12]],
        ),
        type="table",
    )
    himena_ui.exec_action(
        "builtins:plot-3d:line-plot-3d",
        with_params={
            "x": ((0, 99), (0, 1)),
            "y": ((0, 99), (1, 2)),
            "z": ((0, 99), (2, 3)),
        }
    )
    win_3d = himena_ui.current_window
    path = Path(tmpdir) / "test.plot.json"
    himena_ui.current_window.write_model(path)
    himena_ui.read_file(path)
    himena_ui.exec_action("builtins:plot:plot-to-dataframe", with_params={"component": 0})
    himena_ui.exec_action("builtins:plot:plot-to-dataframe", with_params={"component": 0}, window_context=win_3d)

def test_bar_plot_via_command(make_himena_ui, tmpdir):
    himena_ui: MainWindow = make_himena_ui()
    win = himena_ui.add_object(
        _str_array(
            [["x", "y", "z"],
             [0, 4, 6],
             [1, 6, 10],
             [2, 5, 12]],
        ),
        type="table",
    )
    himena_ui.current_window  = win
    himena_ui.exec_action(
        "builtins:bar-plot",
        with_params={
            "x": ((0, 99), (0, 1)),
            "y": ((0, 99), (1, 2)),
            "bottom": None,
            "face": {"color": Color("red"), "hatch": "/"},
            "edge": {"color": Color("blue"), "width": 2.5, "style": "--"},
        }
    )
    himena_ui.current_window  = win
    himena_ui.exec_action(
        "builtins:bar-plot",
        with_params={
            "x": ((0, 99), (0, 1)),
            "y": ((0, 99), (1, 3)),
            "bottom": None,
            "face": {"color": Colormap("tab10"), "hatch": None},
            "edge": {"color": Color("black"), "width": 2, "style": None},
        }
    )
    himena_ui.current_window  = win
    himena_ui.exec_action(
        "builtins:bar-plot",
        with_params={
            "x": ((0, 99), (0, 1)),
            "y": ((0, 99), (2, 3)),
            "bottom": ((0, 99), (1, 2)),
            "face": {"color": Color("red"), "hatch": "/"},
            "edge": {"color": Color("blue"), "width": 2.5, "style": "--"},
        }
    )
    path = Path(tmpdir) / "test.plot.json"
    himena_ui.current_window.write_model(path)
    himena_ui.read_file(path)
    himena_ui.exec_action("builtins:plot:plot-to-dataframe", with_params={"component": 0})

def test_errorbar_plot_via_command(make_himena_ui, tmpdir):
    himena_ui: MainWindow = make_himena_ui("mock")
    win = himena_ui.add_object(
        _str_array(
            [["x", "y", "yerr"],
             [0, 4, 0.5],
             [1, 6, 0.3],
             [2, 5, 0.4]],
        ),
        type="table",
    )
    himena_ui.current_window  = win
    himena_ui.exec_action(
        "builtins:errorbar-plot",
        with_params={
            "x": ((0, 99), (0, 1)),
            "y": ((0, 99), (1, 2)),
            "xerr": None,
            "yerr": ((0, 99), (2, 3)),
            "capsize": 0.1,
            "edge": {"color": Color("blue"), "width": 1, "style": "-"},
        }
    )
    himena_ui.current_window  = win
    himena_ui.exec_action(
        "builtins:errorbar-plot",
        with_params={
            "x": ((0, 99), (0, 1)),
            "y": ((0, 99), (1, 2)),
            "xerr": ((0, 99), (2, 3)),
            "yerr": None,
            "capsize": 0,
            "edge": {"color": Color("blue"), "width": 1, "style": "-"},
        }
    )
    himena_ui.current_window  = win
    himena_ui.exec_action(
        "builtins:errorbar-plot",
        with_params={
            "x": ((0, 99), (0, 1)),
            "y": ((0, 99), (1, 2)),
            "xerr": ((0, 99), (2, 3)),
            "yerr": ((0, 99), (2, 3)),
            "capsize": 0.,
            "edge": {"color": Color("blue"), "width": 1, "style": "-"},
        }
    )
    path = Path(tmpdir) / "test.plot.json"
    himena_ui.current_window.write_model(path)
    himena_ui.read_file(path)
    himena_ui.exec_action("builtins:plot:plot-to-dataframe", with_params={"component": 0})

def test_band_plot_via_command(make_himena_ui, tmpdir):
    himena_ui: MainWindow = make_himena_ui("mock")
    win = himena_ui.add_object(
        _str_array(
            [["x", "y0", "y1"],
             [0, 4, 6],
             [1, 6, 10],
             [2, 5, 12]],
        ),
        type="table",
    )
    himena_ui.current_window  = win
    himena_ui.exec_action(
        "builtins:band-plot",
        with_params={
            "x": ((0, 99), (0, 1)),
            "y0": ((0, 99), (1, 2)),
            "y1": ((0, 99), (2, 3)),
            "face": {"color": Color("red"), "hatch": "/"},
            "edge": {"color": Color("blue"), "width": 2.5, "style": "--"},
        }
    )
    path = Path(tmpdir) / "test.plot.json"
    himena_ui.current_window.write_model(path)
    himena_ui.read_file(path)
    himena_ui.exec_action("builtins:plot:plot-to-dataframe", with_params={"component": 0})

def test_histogram(make_himena_ui):
    himena_ui: MainWindow = make_himena_ui("mock")
    win = himena_ui.add_object(
        _str_array([["x"], [0], [1], [2], [3.2], [0.2]]),
        type="table",
    )
    himena_ui.exec_action(
        "builtins:histogram",
        with_params={"x": ((0, 99), (0, 1)), "bins": 2}
    )
    win_hist = himena_ui.current_window
    himena_ui.exec_action("builtins:plot:plot-to-dataframe", with_params={"component": 0}, window_context=win_hist)
    himena_ui.exec_action(
        "builtins:edit-plot",
        with_params={
            "x": {"label": "X value"},
            "y": {"label": "Y value", "lim": (0, 1)},
            "title": "Title ...",
        },
        window_context=win_hist,
    )

def test_plot_from_function(himena_ui: MainWindow):
    himena_ui.add_object(
        lambda x: np.sin(x),
        type="function",
        title="sin(x)",
    )
    himena_ui.exec_action(
        "builtins:plot-function-1d",
        with_params={"xmin": -1, "xmax": 1},
    )
    himena_ui.add_object(
        lambda x, y: np.sin(x + y / 2),
        type="function",
        title="sin(x + y / 2)",
    )
    himena_ui.exec_action(
        "builtins:plot-function-2d",
        with_params={"xmin": -2, "xmax": 2, "ymin": -1, "ymax": 1},
    )

def test_plot_model_processing(make_himena_ui):
    himena_ui: MainWindow = make_himena_ui("mock")
    win = himena_ui.add_object(
        _str_array(
            [["x", "y", "z"],
             [0, 4, 6],
             [1, 6, 10],
             [2, 5, 12]],
        ),
        type="table",
    )
    himena_ui.exec_action(
        "builtins:scatter-plot",
        with_params={
            "x": ((0, 3), (0, 1)),
            "y": ((0, 3), (1, 3)),
        }
    )
    himena_ui.exec_action(
        "builtins:plot:select-plot-components",
        with_params={"components": [1]},
    )
    assert len(himena_ui.current_model.value.axes.models) == 1
