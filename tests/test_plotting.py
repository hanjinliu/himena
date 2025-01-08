import os
from pathlib import Path
from cmap import Color, Colormap
import numpy as np
import matplotlib.pyplot as plt

from himena.widgets import MainWindow
import himena.standards.plotting as hplt
from himena_builtins.qt.plot import BACKEND_HIMENA
from himena_builtins.qt.plot._canvas import QMatplotlibCanvas

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

def test_plot_model():
    fig = hplt.figure()
    x = np.arange(5)
    fig.axes.scatter(x, np.sin(x))
    fig.axes.plot(x, np.cos(x / 2))
    fig.axes.bar(x, np.sin(x) / 2)
    fig.axes.errorbar(x, np.cos(x), x_error=np.full(5, 0.2), y_error=np.full(5, 0.1))
    fig.axes.hist(np.sqrt(np.arange(100)), bins=10)
    fig.axes.band(x, np.sin(x) / 2, np.cos(x) / 2)
    fig.axes.title = "Title"
    fig.axes.x.lim = (0, 4)
    fig.axes.y.lim = (-1, 1)
    fig.axes.x.label = "X-axis"
    fig.axes.y.label = "Y-axis"

def test_scatter_plot_via_command(himena_ui: MainWindow, tmpdir):
    win = himena_ui.add_object(
        [["x", "y", "z"],
         [0, 4, 6],
         [1, 6, 10],
         [2, 5, 12]],
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

def test_line_plot_via_command(himena_ui: MainWindow, tmpdir):
    win = himena_ui.add_object(
        [["x", "y", "z"],
         [0, 4, 6],
         [1, 6, 10],
         [2, 5, 12]],
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

def test_bar_plot_via_command(himena_ui: MainWindow, tmpdir):
    win = himena_ui.add_object(
        [["x", "y", "z"],
         [0, 4, 6],
         [1, 6, 10],
         [2, 5, 12]],
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

def test_errorbar_plot_via_command(himena_ui: MainWindow, tmpdir):
    win = himena_ui.add_object(
        [["x", "y", "yerr"],
         [0, 4, 0.5],
         [1, 6, 0.3],
         [2, 5, 0.4]],
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

def test_band_plot_via_command(himena_ui: MainWindow, tmpdir):
    win = himena_ui.add_object(
        [["x", "y0", "y1"],
         [0, 4, 6],
         [1, 6, 10],
         [2, 5, 12]],
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
