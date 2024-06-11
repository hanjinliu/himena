from __future__ import annotations

from timeit import default_timer as timer
from typing import TYPE_CHECKING
from app_model import Application
import logging

if TYPE_CHECKING:
    from royalapp.plugins.core import PluginInterface

_LOGGER = logging.getLogger(__name__)
_ROYALAPP_PLUGIN_VAR = "__royalapp_plugin__"
_DUMMY_APP_NAME = "royalapp-dry-install"
_NO_INTERF = object()


def install_plugins(app: Application, plugins: list[str | PluginInterface]):
    """Install plugins to the application."""
    from importlib import import_module
    from royalapp.plugins.core import PluginInterface

    for name in plugins:
        _time_0 = timer()
        if isinstance(name, str):
            if name.endswith(".py"):
                name = name[:-3]
            mod = import_module(name)
            interf = getattr(mod, _ROYALAPP_PLUGIN_VAR, _NO_INTERF)
            if interf is _NO_INTERF:
                # if the plugin only provides reader/writer, importing the submodule
                # is enough.
                pass
            elif not isinstance(interf, PluginInterface):
                raise TypeError(
                    f"Invalid plugin interface type: {type(interf)} in module {name}."
                )
            else:
                interf.install_to(app)
        elif isinstance(name, PluginInterface):
            name.install_to(app)
        else:
            raise TypeError(f"Invalid plugin type: {type(name)}")
        _msec = (timer() - _time_0) * 1000
        _LOGGER.info(f"Plugin {name} installed in {_msec:.3f} msec.")


def dry_install_plugins(plugins: list[str | PluginInterface]):
    """Dry-install plugins to a dummy application."""
    if Application.get_app(_DUMMY_APP_NAME):
        raise RuntimeError("Dummy application already exists.")
    app = Application(_DUMMY_APP_NAME)
    install_plugins(app, plugins)
    Application.destroy(app.name)
