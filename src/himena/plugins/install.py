from __future__ import annotations

from timeit import default_timer as timer
from app_model import Application
import logging

_LOGGER = logging.getLogger(__name__)
_DUMMY_APP_NAME = "himena-dry-install"


def install_plugins(app: Application, plugins: list[str]):
    """Install plugins to the application."""
    from importlib import import_module
    from himena.plugins.actions import install_to

    for name in plugins:
        _time_0 = timer()
        if isinstance(name, str):
            if name.endswith(".py"):
                name = name[:-3]
            try:
                import_module(name)
            except ModuleNotFoundError:
                _LOGGER.error(f"Plugin {name} not found.")
        else:
            raise TypeError(f"Invalid plugin type: {type(name)}")
        _msec = (timer() - _time_0) * 1000
        _LOGGER.info(f"Plugin {name} installed in {_msec:.3f} msec.")
    install_to(app)


def dry_install_plugins(plugins: list[str]):
    """Dry-install plugins to a dummy application."""
    if Application.get_app(_DUMMY_APP_NAME):
        raise RuntimeError("Dummy application already exists.")
    app = Application(_DUMMY_APP_NAME)
    try:
        install_plugins(app, plugins)
    finally:
        Application.destroy(app.name)
