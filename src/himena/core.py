from __future__ import annotations

from typing import TYPE_CHECKING, Sequence, TypeVar
from logging import getLogger
from himena.consts import StandardType
from himena.types import WidgetDataModel
from himena.standards import BaseMetadata
from himena.profile import AppProfile, load_app_profile

if TYPE_CHECKING:
    from himena.widgets import MainWindow

_LOGGER = getLogger(__name__)
_T = TypeVar("_T")


def new_window(
    profile: str | AppProfile | None = None,
    *,
    plugins: Sequence[str] | None = None,
    backend: str = "qt",
) -> MainWindow:
    """Create a new window with the specified profile and additional plugins."""
    from himena._app_model import get_model_app
    from himena.widgets._initialize import init_application
    from himena.plugins import install_plugins, override_keybindings

    plugins = list(plugins or [])

    # NOTE: the name of AppProfile and the app_model.Application must be the same.
    if isinstance(profile, str):
        app_prof = load_app_profile(profile)
    elif isinstance(profile, AppProfile):
        app_prof = profile
    elif profile is None:
        try:
            app_prof = load_app_profile("default")
        except ValueError:
            app_prof = AppProfile.default(save=True)
    else:
        raise TypeError("`profile` must be a str or an AppProfile object.")
    model_app = get_model_app(app_prof.name)
    plugins = app_prof.plugins + plugins
    if plugins:
        install_plugins(model_app, plugins)

    # create the main window
    init_application(model_app)
    override_keybindings(model_app, app_prof)
    main_window = _get_main_window(backend, model_app, theme=app_prof.theme)

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


def create_model(
    value: _T,
    *,
    type: str | None = None,
    title: str | None = None,
    extension_default: str | None = None,
    extensions: list[str] | None = None,
    metadata: object | None = None,
    force_open_with: str | None = None,
    editable: bool = True,
) -> WidgetDataModel[_T]:
    """Helper function to create a WidgetDataModel."""
    if type is None:
        if isinstance(metadata, BaseMetadata):
            type = metadata.expected_type()
    if type is None:
        type = StandardType.ANY
    return WidgetDataModel(
        value=value,
        type=type,
        title=title,
        extension_default=extension_default,
        extensions=extensions or [],
        metadata=metadata,
        force_open_with=force_open_with,
        editable=editable,
    )


def _get_main_window(backend: str, *args, **kwargs) -> MainWindow:
    if backend == "qt":
        from himena.qt import MainWindowQt

        return MainWindowQt(*args, **kwargs)
    elif backend == "mock":
        from himena.mock import MainWindowMock

        return MainWindowMock(*args, **kwargs)
    raise ValueError(f"Invalid backend: {backend}")
