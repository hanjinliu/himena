# Plotting in Himena

`himena` supports `matplotlib` plotting by default. You can pass a `Figure` object and
the type `"matplotlib-figure"` (`StandardType.MPL_FIGURE`) to a `WidgetDataModel` to
create a sub-window with a `matplotlib` figure.

However, directly using `matplotlib` object is not the best way to plot in `himena`
because of the following reasons:

- The plot is not serializable. You cannot save the plot in a structured way.
- The plot result cannot be reused in other plot backends.

`himena` provides a standard plotting interface to create plots.

## Plotting Standard

The standard objects and plotting API are defined in [`himena.standards.plotting`][himena.standards.plotting].

``` python
from himena.standards import plotting as hplt
```

Many methods are similar to `matplotlib`. You can run following code in the Python
interpreter console (++ctrl+shift+i++) to see the plot.

``` python
import numpy as np

fig = hplt.figure()
x = np.linspace(0, 1, 100)
y = np.sin(x * 2 * np.pi)
fig.scatter(x, y, face_color="yellow", edge_color="black")
fig.plot(x, -x, color="gray", style="--")
fig.show()  # add to the current main window
```

What the functions do is just udpating the standard plotting models. They are converted
to `matplotlib` object inside the plugin.
