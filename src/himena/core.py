from __future__ import annotations

from typing import TYPE_CHECKING
from app_model import Application
from himena.profile import AppProfile, load_app_profile

if TYPE_CHECKING:
    from himena.plugins.core import PluginInterface
    from himena.widgets import MainWindow
    from qtpy import QtWidgets as QtW


def new_window(
    profile: str | AppProfile | None = None,
    *,
    plugins: list[str | PluginInterface] = [],
    app: str = "himena",
) -> MainWindow[QtW.QWidget]:
    from himena.qt import MainWindowQt

    model_app = Application.get_or_create(app)
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
        from himena.plugins import install_plugins

        install_plugins(model_app, plugins)
    main_window = MainWindowQt(model_app)
    main_window._backend_main_window._update_context()
    return main_window
