import numpy as np
import matplotlib.pyplot as plt
from himena import new_window, StandardType
from himena import plotting as hplt

if __name__ == "__main__":
    ui = new_window()
    x = np.linspace(0, 10, 100)
    y0 = np.sin(x) * np.exp(-x / 3)
    y1 = np.cos(x) * np.exp(-x / 3)
    y_noisy = y0 + np.random.normal(0, 0.1, size=x.shape)

    # himena plotting has an interface similar to matplotlib.
    fig = hplt.figure()
    fig.plot(x, y0, name="sin(x) * exp(-x/3)", color="blue")
    fig.plot(x, y1, name="cos(x) * exp(-x/3)", color="red", style=":")
    fig.scatter(x, y_noisy, face_color="transparent", edge_color="gray", edge_width=2)
    fig.title = "himena standard plot"
    ui.add_object(fig, type=StandardType.PLOT, title="Simple plot")

    # you can also directly add a matplotlib figure.
    fig = plt.figure()
    plt.plot(x, y0, label="sin(x) * exp(-x/3)", color="blue")
    plt.plot(x, y1, label="cos(x) * exp(-x/3)", color="red", linestyle=":")
    plt.scatter(x, y_noisy, facecolor="#00000000", edgecolor="gray", linewidth=2)
    plt.legend()
    plt.title("matplotlib direct plot")
    ui.add_object(fig, type=StandardType.MPL_FIGURE, title="Matplotlib plot")
    ui.show(run=True)
