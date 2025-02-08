from __future__ import annotations

import os
from himena.plugins import register_widget_class
from himena.consts import StandardType
from himena.utils.misc import lru_cache


BACKEND_HIMENA = "module://himena_builtins.qt.plot._canvas"


@lru_cache(maxsize=1)
def _is_matplotlib_available() -> bool:
    import importlib.metadata

    try:
        importlib.metadata.distribution("matplotlib")
    except importlib.metadata.PackageNotFoundError:
        return False
    return True


def register_mpl_widget():
    # Update the matplotlib default backend
    os.environ["MPLBACKEND"] = BACKEND_HIMENA
    if not _is_matplotlib_available():
        return

    register_widget_class(StandardType.PLOT, model_matplotlib_canvas, priority=0)
    register_widget_class(StandardType.MPL_FIGURE, matplotlib_canvas, priority=0)


def model_matplotlib_canvas():
    from himena_builtins.qt.plot._canvas import QModelMatplotlibCanvas

    return QModelMatplotlibCanvas()


model_matplotlib_canvas.__himena_widget_id__ = "builtins:QModelMatplotlibCanvas"
model_matplotlib_canvas.__himena_display_name__ = "Built-in Plot Canvas"


def matplotlib_canvas():
    from himena_builtins.qt.plot._canvas import QMatplotlibCanvas

    return QMatplotlibCanvas()


matplotlib_canvas.__himena_widget_id__ = "builtins:QMatplotlibCanvas"
matplotlib_canvas.__himena_display_name__ = "Matplotlib Canvas"

register_mpl_widget()
