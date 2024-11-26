import os
from pathlib import Path
from pytestqt.qtbot import QtBot
import numpy as np
import matplotlib.pyplot as plt

from himena.widgets import MainWindow
from himena import plotting as hplt
from himena.builtins.qt.plot import BACKEND_HIMENA
from himena.builtins.qt.plot._canvas import QMatplotlibCanvas

def test_direct_plot(ui: MainWindow):
    assert os.environ["MPLBACKEND"] == BACKEND_HIMENA
    plt.switch_backend(BACKEND_HIMENA)
    tab = ui.add_tab()
    plt.figure(figsize=(3, 3))
    assert len(tab) == 0
    plt.plot([0, 1, 2])
    plt.show()
    assert len(tab) == 1
    assert isinstance(tab[0].widget, QMatplotlibCanvas)

def test_plot_model(ui: MainWindow):
    tab = ui.add_tab()
    fig = hplt.figure()
    x = np.arange(5)
    fig.axes.scatter(x, np.sin(x))
    fig.axes.plot(x, np.cos(x / 2))
    fig.axes.bar(x, np.sin(x) / 2)
    fig.axes.errorbar(x, np.cos(x), x_error=np.full(5, 0.2), y_error=np.full(5, 0.1))
    fig.axes.title = "Title"
    fig.axes.x.lim = (0, 4)
    fig.axes.y.lim = (-1, 1)
    fig.axes.x.label = "X-axis"
    fig.axes.y.label = "Y-axis"
