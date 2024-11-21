from __future__ import annotations

import os
from himena.qt import register_widget
import pkg_resources

BACKEND_HIMENA = "module://himena.builtins.qt.plot._canvas"


def register_mpl_widget():
    # Update the matplotlib default backend
    os.environ["MPLBACKEND"] = BACKEND_HIMENA

    if not any(dist.key == "matplotlib" for dist in pkg_resources.working_set):
        return

    from himena.builtins.qt.plot._canvas import QMatplotlibCanvas

    register_widget("matplotlib-figure", QMatplotlibCanvas)


register_mpl_widget()
