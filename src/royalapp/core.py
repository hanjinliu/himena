from __future__ import annotations

from typing import TYPE_CHECKING
from app_model import Application
from royalapp.profile import AppProfile, load_app_profile

if TYPE_CHECKING:
    from royalapp.plugins.core import PluginInterface
    from royalapp.widgets import MainWindow
    from qtpy import QtWidgets as QtW


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
        from royalapp.plugins import install_plugins

        install_plugins(app, plugins)
    main_window = MainWindowQt(app)
    main_window._backend_main_window._update_context()
    return main_window
