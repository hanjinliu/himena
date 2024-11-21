from __future__ import annotations

import os
from himena.qt import register_widget
from himena._utils import lru_cache

BACKEND_HIMENA = "module://himena.builtins.qt.plot._canvas"


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
    from himena.builtins.qt.plot._canvas import QMatplotlibCanvas

    register_widget("matplotlib-figure", QMatplotlibCanvas)


register_mpl_widget()
