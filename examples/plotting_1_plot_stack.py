import numpy as np
from himena import new_window, StandardType
from himena import plotting as hplt

# A plot stack is a collection of plots that can be controlled by sliders (using the
# default widget).

if __name__ == "__main__":
    ui = new_window()
    n_time = 10
    fig = hplt.figure_stack(n_time, multi_dims=["time"])
    x = np.linspace(0, 30, 256)
    v = 1.6
    for t in range(n_time):
        y = np.sin(x + v * t)
        fig[t].plot(x, y * np.exp(-t / 10), color="blue")
        fig[t].text([1], [0.9], [f"t={t}"], color="black")
    fig.x.label = "X-axis"
    fig.y.label = "Y-axis"
    ui.add_object(fig, type=StandardType.PLOT_STACK, title="Stacked Plot")
    ui.show(run=True)
