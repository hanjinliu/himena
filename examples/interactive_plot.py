# This example demonstrates how to create an interactive plot using himena.
# The `add_function` method is used to convert a function into a parametric widget.
# Because the `preview` argument is set to `True`, the function is executed immediately
# for previewing when the parameter changed.

import numpy as np
from himena import new_window
from himena.standards import plotting as hplt
from himena.types import WidgetDataModel
from himena.consts import StandardType

def plot_sin_curve(a: float = 1.0, b: float = 1.0, phi: float = 0.0) -> WidgetDataModel:
    x = np.linspace(-np.pi, np.pi, 100)
    y = a * np.sin(b * x + phi)
    fig = hplt.figure()
    fig.plot(x, y, color="red")
    return WidgetDataModel(value=fig, type=StandardType.PLOT)

if __name__ == "__main__":
    ui = new_window()
    ui.add_function(
        plot_sin_curve,
        preview=True,
        title="Plot in new window",
    )
    ui.add_function(
        plot_sin_curve,
        preview=True,
        result_as="below",
        title="Plot below the parameters",
    )
    ui.show(run=True)
