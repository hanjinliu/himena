from __future__ import annotations

from typing import TYPE_CHECKING
import logging
from timeit import default_timer as timer
from app_model import Application
from royalapp.profile import AppProfile, load_app_profile

if TYPE_CHECKING:
    from royalapp.plugins.core import PluginInterface
    from royalapp.widgets import MainWindow
    from qtpy import QtWidgets as QtW

_LOGGER = logging.getLogger(__name__)


def new_window(
    profile: str | AppProfile | None = None,
    *,
    plugins: list[str | PluginInterface] = [],
    app: str = "royalapp",
) -> MainWindow[QtW.QWidget]:
    from royalapp.qt import MainWindowQt

    app = Application.get_or_create(app)
    plugins = list(plugins)
    if isinstance(profile, str):
        app_prof = load_app_profile(profile)
        plugins = app_prof.plugins + plugins
    elif isinstance(profile, AppProfile):
        plugins = profile.plugins + plugins
    elif profile is None:
        plugins = AppProfile().plugins + plugins
    else:
        raise TypeError("`profile` must be a str or an AppProfile object.")
    if plugins:
        install_plugins(app, plugins)
    main_window = MainWindowQt(app)
    main_window._backend_main_window._update_context()
    return main_window


_ROYALAPP_PLUGIN_VAR = "__royalapp_plugin__"
_NO_INTERF = object()


def install_plugins(app: Application, plugins: list[str | PluginInterface]):
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
