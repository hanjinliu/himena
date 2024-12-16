from __future__ import annotations

import os
from himena.plugins import register_widget_class
from himena.consts import StandardType
from himena._utils import lru_cache
from himena_builtins.qt.plot._conversion import register_plot_model

__all__ = ["register_plot_model"]

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
    from himena_builtins.qt.plot._canvas import (
        QMatplotlibCanvas,
        QModelMatplotlibCanvas,
    )

    register_widget_class(StandardType.PLOT, QModelMatplotlibCanvas, priority=0)
    register_widget_class(StandardType.MPL_FIGURE, QMatplotlibCanvas, priority=0)


register_mpl_widget()
