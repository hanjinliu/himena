from __future__ import annotations

from pathlib import Path
from timeit import default_timer as timer
from app_model import Application
import logging

_LOGGER = logging.getLogger(__name__)


def install_plugins(app: Application, plugins: list[str]):
    """Install plugins to the application."""
    from importlib import import_module
    from himena.plugins import AppActionRegistry

    reg = AppActionRegistry.instance()
    for name in plugins:
        if name in reg._installed_plugins:
            continue
        _time_0 = timer()
        if isinstance(name, str):
            if name.endswith(".py"):
                if not Path(name).exists():
                    _LOGGER.error(f"Plugin file {name} not found.")
                    continue
                import runpy

                runpy.run_path(name)
            else:
                try:
                    import_module(name)
                except ModuleNotFoundError:
                    _LOGGER.error(f"Plugin {name} not found.")
        else:
            raise TypeError(f"Invalid plugin type: {type(name)}")
        _msec = (timer() - _time_0) * 1000
        _LOGGER.info(f"Plugin {name} installed in {_msec:.3f} msec.")
    reg.install_to(app)
    reg._installed_plugins.extend(plugins)
