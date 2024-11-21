from __future__ import annotations

from typing import TYPE_CHECKING
from logging import getLogger
from himena.profile import AppProfile, load_app_profile

if TYPE_CHECKING:
    from himena.widgets import MainWindow
    from qtpy import QtWidgets as QtW

_LOGGER = getLogger(__name__)


def new_window(
    profile: str | AppProfile | None = None,
    *,
    plugins: list[str] = [],
) -> MainWindow[QtW.QWidget]:
    """Create a new window with the specified profile and additional plugins."""
    from himena.qt import MainWindowQt
    from himena._app_model import get_model_app
    from himena.widgets._initialize import init_application

    plugins = list(plugins)
    if isinstance(profile, str):
        app_prof = load_app_profile(profile)
    elif isinstance(profile, AppProfile):
        app_prof = profile
    elif profile is None:
        app_prof = AppProfile.default(save=True)
    else:
        raise TypeError("`profile` must be a str or an AppProfile object.")
    model_app = get_model_app(app_prof.name)
    plugins = app_prof.plugins + plugins
    if plugins:
        from himena.plugins import install_plugins

        install_plugins(model_app, plugins)
    # create the main window
    init_application(model_app)
    main_window = MainWindowQt(model_app, theme=app_prof.theme)

    # execute startup commands (don't raise exceptions, just log them)
    exceptions: list[tuple[str, dict, Exception]] = []
    for cmd, kwargs in app_prof.startup_commands:
        try:
            main_window.exec_action(cmd, with_params=kwargs)
        except Exception as e:
            exceptions.append((cmd, kwargs, e))
    if exceptions:
        _LOGGER.error("Exceptions occurred during startup commands:")
        for cmd, kwargs, exc in exceptions:
            _LOGGER.error("  %r (parameters=%r): %s", cmd, kwargs, exc)
    return main_window
