from matplotlib import pyplot as plt
from qtpy.QtCore import Qt, QPoint
from pytestqt.qtbot import QtBot
from himena import plotting as hplt, create_model, StandardType
from himena.standards.model_meta import DimAxis
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
    canvas._make_context_menu()
    canvas._copy_canvas()
    qtbot.mouseDClick(canvas, Qt.MouseButton.LeftButton, pos=QPoint(10, 10))
    qtbot.mousePress(canvas, Qt.MouseButton.LeftButton, pos=QPoint(10, 10))
    qtbot.mouseMove(canvas, pos=QPoint(20, 20))
    qtbot.mouseRelease(canvas, Qt.MouseButton.LeftButton, pos=QPoint(20, 20))
    plt.close(fig)

def test_model_matplotlib_canvas_single(qtbot: QtBot):
    fig = hplt.figure()
    canvas = QModelMatplotlibCanvas()
    canvas.update_model(create_model(fig, type=StandardType.PLOT))
    qtbot.addWidget(canvas)
    with WidgetTester(canvas) as tester:
        tester.update_model(value=fig, type=StandardType.PLOT)
        tester.cycle_model()
    canvas._make_context_menu()
    canvas._copy_canvas()

def test_model_matplotlib_canvas_3d(qtbot: QtBot):
    fig = hplt.figure_3d()
    fig.axes.scatter([1, 2, 3], [4, 5, 6], [7, 8, 9])
    fig.axes.plot([1, 2, 3], [4, 5, 6], [7, 8, 9])
    fig.axes.x.label = "X Axis"
    fig.axes.y.label = "Y Axis"
    fig.axes.z.label = "Z Axis"
    fig.axes.title = "3D Plot"
    canvas = QModelMatplotlibCanvas()
    canvas.update_model(create_model(fig, type=StandardType.PLOT))
    qtbot.addWidget(canvas)
    with WidgetTester(canvas) as tester:
        tester.update_model(value=fig, type=StandardType.PLOT)
        tester.cycle_model()
    canvas._make_context_menu()
    canvas._copy_canvas()


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

    fig = hplt.figure_stack(4, multi_dims="time")
    assert fig.shape == (4,)
    fig = hplt.figure_stack(
        2, 2,
        multi_dims=[
            "time",
            DimAxis(name="slice", scale=0.5, unit="mm", labels=["S0", "S1"]),
        ]
    )
    assert fig.shape == (2, 2)
