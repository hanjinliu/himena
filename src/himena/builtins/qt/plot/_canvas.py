from __future__ import annotations

from typing import TYPE_CHECKING

from matplotlib.backends.backend_qtagg import (
    FigureCanvasQTAgg,
    NavigationToolbar2QT,
)
from qtpy import QtWidgets as QtW
from himena.plugins import protocol_override
from himena.types import WidgetDataModel

if TYPE_CHECKING:
    from matplotlib.figure import Figure


class QMatplotlibCanvas(QtW.QWidget):
    def __init__(self):
        super().__init__()
        layout = QtW.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._canvas = None
        self._toolbar = None

    @property
    def figure(self) -> Figure:
        return self._canvas.figure

    @protocol_override
    def update_model(self, model: WidgetDataModel[Figure]):
        self._canvas = FigureCanvasQTAgg(model.value)
        self._toolbar = NavigationToolbar2QT(self._canvas, self)
        self.layout().addWidget(self._canvas)

    @protocol_override
    def control_widget(self) -> QtW.QWidget:
        return self._toolbar

    @protocol_override
    def size_hint(self) -> tuple[int, int]:
        return 400, 300


FigureCanvas = FigureCanvasQTAgg


# The plt.show function will be overwriten to this.
# Modified from matplotlib_inline (BSD 3-Clause "New" or "Revised" License)
# https://github.com/ipython/matplotlib-inline
def show(close=True, block=None):
    import matplotlib.pyplot as plt
    from matplotlib._pylab_helpers import Gcf
    from himena.widgets import current_instance

    ui = current_instance()

    try:
        for figure_manager in Gcf.get_all_fig_managers():
            ui.add_data(
                figure_manager.canvas.figure, type="matplotlib-figure", title="Plot"
            )
    finally:
        show._called = True
        if close and Gcf.get_all_fig_managers():
            plt.close("all")


show._called = False
