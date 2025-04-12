import pytest
import numpy as np
from himena.standards import plotting as hplt

def test_subplots():
    row = hplt.row(2)
    row[0].plot([0, 1, 2], [3, 0, -2])
    row[1].scatter([0, 1, 2], [3, 0, -2])
    with pytest.raises(IndexError):
        row[2]

    col = hplt.column(2)
    col[0].plot([0, 1, 2], [3, 0, -2])
    col[1].scatter([0, 1, 2], [3, 0, -2])
    with pytest.raises(IndexError):
        col[2]

def test_plot_model():
    fig = hplt.figure()
    x = np.arange(5)
    fig.scatter(x, np.sin(x))
    fig.scatter(np.sin(x), edge_width=2)
    fig.plot(np.cos(x / 2), color="blue")
    fig.plot(x, np.cos(x / 2), color="blue", alpha=0.5)
    fig.bar(x, np.sin(x) / 2)
    fig.bar(np.sin(x) / 2, color="red")
    fig.bar(x, np.sin(x) / 2, color="red", edge_color="blue", edge_alpha=0.7)
    fig.errorbar(x, np.cos(x), x_error=np.full(5, 0.2), y_error=np.full(5, 0.1))
    fig.hist(np.sqrt(np.arange(100)), bins=10)
    fig.hist(np.sqrt(np.arange(100)), bins=19, orient="horizontal", stat="density")
    fig.hist(np.sqrt(np.arange(100)), bins=12, stat="probability")
    fig.band(x, np.sin(x) / 2, np.cos(x) / 2)
    fig.text([0, 1], [4, 3], ["A", "B"])
    fig.axes.title = "Title"
    fig.axes.x.lim = (0, 4)
    fig.axes.y.lim = (-1, 1)
    fig.axes.x.label = "X-axis"
    fig.axes.y.label = "Y-axis"
    fig.axes.axis_color = "red"

    # use figure properties
    fig.title = "Title"
    assert fig.title == "Title"
    fig.x.lim = (0, 5)
    assert fig.x.lim == (0, 5)
    fig.y.lim = (-1, 2)
    assert fig.y.lim == (-1, 2)
    fig.x.label = "X"
    assert fig.x.label == "X"
    fig.y.label = "Y"
    assert fig.y.label == "Y"
    fig.axis_color = "blue"
    assert fig.axis_color == "blue"
