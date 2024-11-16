from __future__ import annotations

from typing import TYPE_CHECKING
from himena.profile import AppProfile, load_app_profile

if TYPE_CHECKING:
    from himena.widgets import MainWindow
    from qtpy import QtWidgets as QtW


def new_window(
    profile: str | AppProfile | None = None,
    *,
    plugins: list[str] = [],
    app: str = "himena",
) -> MainWindow[QtW.QWidget]:
    from himena.qt import MainWindowQt
    from himena._app_model import get_model_app

    model_app = get_model_app(app)
    plugins = list(plugins)
    if isinstance(profile, str):
        app_prof = load_app_profile(profile)
    elif isinstance(profile, AppProfile):
        app_prof = profile
    elif profile is None:
        app_prof = AppProfile.default()
    else:
        raise TypeError("`profile` must be a str or an AppProfile object.")
    plugins = app_prof.plugins + plugins
    if plugins:
        from himena.plugins import install_plugins

        install_plugins(model_app, plugins)
    main_window = MainWindowQt(model_app, theme=app_prof.theme)
    main_window._backend_main_window._update_context()
    return main_window
