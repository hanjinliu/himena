from matplotlib import pyplot as plt
from pytestqt.qtbot import QtBot
from himena import plotting as hplt, create_model, StandardType
from himena.testing import WidgetTester
from himena_builtins.qt.plot._canvas import QMatplotlibCanvas, QModelMatplotlibCanvas, QModelMatplotlibCanvasStack

def test_matplotlib_canvas(qtbot: QtBot):
    plt.switch_backend("Agg")
    fig = plt.figure()
    canvas = QMatplotlibCanvas()
    qtbot.addWidget(canvas)
    canvas.update_model(create_model(fig, type=StandardType.PLOT))
    with WidgetTester(canvas) as tester:
        tester.to_model()
    plt.close(fig)

def test_model_matplotlib_canvas_single(qtbot: QtBot):
    fig = hplt.figure()
    canvas = QModelMatplotlibCanvas()
    canvas.update_model(create_model(fig, type=StandardType.PLOT))
    qtbot.addWidget(canvas)
    with WidgetTester(canvas) as tester:
        tester.update_model(value=fig, type=StandardType.PLOT)
        tester.cycle_model()

def test_model_matplotlib_canvas_row(qtbot: QtBot):
    fig = hplt.row(2)
    fig[0].plot([1, 2, 3])
    fig[1].scatter([4, 5, 6])
    canvas = QModelMatplotlibCanvas()
    canvas.update_model(create_model(fig, type=StandardType.PLOT))
    qtbot.addWidget(canvas)
    with WidgetTester(canvas) as tester:
        tester.cycle_model()

def test_model_matplotlib_canvas_col(qtbot: QtBot):
    fig = hplt.column(2)
    fig[0].bar([1, 2, 3])
    fig[1].errorbar([4, 5, 6])
    canvas = QModelMatplotlibCanvas()
    canvas.update_model(create_model(fig, type=StandardType.PLOT))
    qtbot.addWidget(canvas)
    with WidgetTester(canvas) as tester:
        tester.cycle_model()

def test_model_matplotlib_canvas_stack(qtbot: QtBot):
    fig = hplt.figure_stack(2, 2)
    assert fig.shape == (2, 2)
    fig.axes[0, 0].plot([1, 2, 3])
    fig.axes[0, 1].plot([4, 5, 6])
    fig[1, 0].plot([7, 8, 9])
    fig[1, 1].plot([10, 11, 12])
    fig.x.label = "x"
    fig.y.label = "y"
    fig.title = "title"
    fig.axis_color = "pink"
    canvas = QModelMatplotlibCanvasStack()
    canvas.update_model(create_model(fig, type=StandardType.PLOT_STACK))
    qtbot.addWidget(canvas)
    with WidgetTester(canvas) as tester:
        tester.cycle_model()
