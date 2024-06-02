from __future__ import annotations

from typing import TYPE_CHECKING
from app_model import Application

if TYPE_CHECKING:
    from royalapp.plugins.core import PluginInterface
    from royalapp.widgets import MainWindow
    from qtpy import QtWidgets as QtW


def new_window(
    app: str = "royalapp",
    plugins: list[str | PluginInterface] = [],
) -> MainWindow[QtW.QWidget]:
    from royalapp.qt import MainWindowQt

    if plugins:
        plugins = plugins.copy()
        install_plugins(Application.get_or_create(app), plugins)
    return MainWindowQt(app)


_ROYALAPP_PLUGIN_VAR = "__royalapp_plugin__"


def install_plugins(app: Application, plugins: list[str | PluginInterface]):
    from importlib import import_module
    from royalapp.plugins.core import PluginInterface

    for name in plugins:
        if isinstance(name, str):
            mod = import_module(name)
            if not hasattr(mod, _ROYALAPP_PLUGIN_VAR):
                raise AttributeError(
                    f"Plugin interface not found in module {name}. Please define a "
                    f"variable named {_ROYALAPP_PLUGIN_VAR!r} in the module."
                )
            interf = getattr(mod, _ROYALAPP_PLUGIN_VAR)
            if not isinstance(interf, PluginInterface):
                raise TypeError(
                    f"Invalid plugin interface type: {type(interf)} in module {name}."
                )
            interf.install_to(app)
        elif isinstance(name, PluginInterface):
            name.install_to(app)
        else:
            raise TypeError(f"Invalid plugin type: {type(name)}")
