from himena._app_model._context import AppContext
from himena._app_model._application import get_model_app, HimenaApplication
from himena._app_model._command_registry import CommandsRegistry

__all__ = ["AppContext", "get_model_app", "CommandsRegistry", "HimenaApplication"]

from app_model import __version__ as app_model_version  # noqa: F401
from app_model.backends.qt import QMenuItemAction, QModelMenu, _qmenu
from qtpy import QT6


def _update_from_context(actions, ctx, _recurse=False):
    try:
        for action in actions:
            if isinstance(action, QMenuItemAction):
                action.update_from_context(ctx)
            elif isinstance(menu := action.menu(), QModelMenu):
                menu.update_from_context(ctx)
    except AttributeError as e:  # pragma: no cover
        raise AttributeError(f"This version of Qt is not supported: {e}") from e


if QT6 and app_model_version < "0.3.2":
    # patch the update_from_context method to handle the bug #232
    _qmenu._update_from_context = _update_from_context  # type: ignore[assignment]

del app_model_version, _qmenu, _update_from_context, QT6
