from cmap import Color
import pytest
import numpy as np
from himena.standards import plotting as hplt
from himena.standards.plotting.layout import BaseLayoutModel

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
    fig.span(2, 4)
    fig.axes.title = "Title"
    assert fig.axes.title == "Title"
    fig.axes.x.lim = (0, 4)
    fig.axes.y.lim = (-1, 1)
    fig.axes.x.label = "X-axis"
    fig.axes.y.label = "Y-axis"
    fig.axes.axis_color = "red"
    assert fig.axes.axis_color == Color("red")

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

def test_grids():
    grid = hplt.grid(2, 2)
    grid[0, 0].plot([0, 1, 2], [3, 0, -2])
    grid[0, 1].scatter([0, 1, 2], [3, 0, -2])
    grid[1, 0].bar([0, 1, 2], [3, 0, -2])
    grid[1, 1].hist(np.sqrt(np.arange(100)), bins=10)
    with pytest.raises(IndexError):
        grid[2, 0]
    with pytest.raises(IndexError):
        grid[0, 2]
    s = grid.model_dump_typed()
    _type = s.pop("type")
    grid_out = BaseLayoutModel.construct(_type, s)
    assert isinstance(grid_out, hplt.Grid)
    assert len(grid[0, 0].models) == 1
    assert isinstance(grid[0, 0].models[0], hplt.models.Line)
    assert len(grid[1, 0].models) == 1
    assert isinstance(grid[1, 0].models[0], hplt.models.Bar)
    assert len(grid[0, 1].models) == 1
    assert isinstance(grid[0, 1].models[0], hplt.models.Scatter)
    assert len(grid[1, 1].models) == 1
    assert isinstance(grid[1, 1].models[0], hplt.models.Histogram)

def test_1d_layout():
    row = hplt.row(2)
    col = hplt.column(2)
    row[0].plot([0, 1, 2], [3, 0, -2])
    row[1].scatter([0, 1, 2], [3, 0, -2])
    col[1].scatter([0, 1, 2], [3, 0, -2])
    col[0].plot([0, 1, 2], [3, 0, -2])
    with pytest.raises(IndexError):
        row[2]
    with pytest.raises(IndexError):
        col[2]
    s = row.model_dump_typed()
    _type = s.pop("type")
    row_out = BaseLayoutModel.construct(_type, s)
    assert isinstance(row_out, hplt.Row)
    assert len(row[0].models) == 1
    assert isinstance(row[0].models[0], hplt.models.Line)
    assert len(row[1].models) == 1
    assert isinstance(row[1].models[0], hplt.models.Scatter)

    s = col.model_dump_typed()
    _type = s.pop("type")
    col_out = BaseLayoutModel.construct(_type, s)
    assert isinstance(col_out, hplt.Column)
    assert len(col[0].models) == 1
    assert isinstance(col[0].models[0], hplt.models.Line)
    assert len(col[1].models) == 1
    assert isinstance(col[1].models[0], hplt.models.Scatter)
