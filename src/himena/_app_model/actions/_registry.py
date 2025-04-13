from __future__ import annotations

from typing import TypeVar, Callable
from app_model.types import Action, SubmenuItem

from himena._utils import make_function_callback
from himena.consts import NO_RECORDING_FIELD

_F = TypeVar("_F", bound=Callable)


class ActionList(list[Action]):
    def append_from_fn(
        self,
        id: str,
        title: str | None = None,
        icon: str | None = None,
        menus=None,
        enablement=None,
        keybindings=None,
        need_function_callback: bool = False,
        run_async: bool = False,
        recording: bool = True,  # whether to add the the command history
    ) -> Callable[[_F], _F]:
        def inner(fn: _F) -> _F:
            if need_function_callback or run_async:
                callback = make_function_callback(
                    fn, id, title=title, run_async=run_async
                )
            else:
                callback = fn
            if not recording:
                setattr(callback, NO_RECORDING_FIELD, True)
            action = Action(
                id=id,
                title=title or id,
                icon=icon,
                callback=callback,
                tooltip=fn.__doc__,
                status_tip=fn.__doc__,
                menus=menus,
                keybindings=keybindings,
                enablement=enablement,
                icon_visible_in_menu=False,
            )
            self.append(action)
            return fn

        return inner


class SubmenuList(list[tuple[str, SubmenuItem]]):
    def append_from(
        self,
        id: str,
        submenu: str,
        title: str,
        enablement=None,
        group: str | None = None,
    ) -> SubmenuList:
        self.append(
            (
                id,
                SubmenuItem(
                    submenu=submenu, title=title, enablement=enablement, group=group
                ),
            )
        )
        return self


ACTIONS = ActionList()
SUBMENUS = SubmenuList()
