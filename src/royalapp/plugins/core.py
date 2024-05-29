from __future__ import annotations

from pathlib import PurePosixPath
from typing import Callable, TypeVar, overload

from app_model import Application
from app_model.types import SubmenuItem
from royalapp.widgets import get_application

_F = TypeVar("_F", bound=Callable)


class PluginInterface:
    def __init__(self, app: str | Application, place: str | PurePosixPath = "."):
        self._app = get_application(app) if isinstance(app, str) else app
        self._place = PurePosixPath(place)

    def add_child(self, id_: str, title: str | None = None, enablement=None) -> None:
        if title is None:
            title = id_.title()
        item = SubmenuItem(title=title, submenu=str(self._place), enablement=enablement)
        self._app.menus.append_menu_items([(id_, item)])
        return self.__class__(self._app, self._place.joinpath(id_))

    @overload
    def register_function(
        self,
        func: None = None,
        *,
        title: str | None = None,
        enablement=None,
    ) -> None: ...
    @overload
    def register_function(
        self,
        func: _F,
        *,
        title: str | None = None,
        enablement=None,
    ) -> _F: ...

    def register_function(self, func=None, *, title=None, enablement=None) -> None:
        def _inner(f: _F) -> _F:
            if title is None:
                _title = f.__name__.replace("_", " ").title()
            else:
                _title = title
            self._app.register_action(
                action=f.__qualname__,
                title=_title,
                callback=f,
                menus=[str(self._place)],
                enablement=enablement,
            )

        return _inner if func is None else _inner(func)


def get_plugin_interface(app: str, menu_id: str) -> PluginInterface:
    out = PluginInterface(app, menu_id)
    return out
