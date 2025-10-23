from __future__ import annotations

from typing import TYPE_CHECKING, Iterator
from himena.consts import MenuId

if TYPE_CHECKING:
    from himena._app_model import HimenaApplication


def is_root_menu_id(app: HimenaApplication, menu_id: str) -> bool:
    if menu_id in (MenuId.TOOLBAR, MenuId.CORNER, app.menus.COMMAND_PALETTE_ID):
        return False
    if len(menu_id) == 0:
        return False
    return "/" not in menu_id.replace("//", "")


def iter_root_menu_ids(app: HimenaApplication) -> Iterator[str]:
    skip = (MenuId.FILE, MenuId.WINDOW, MenuId.VIEW, MenuId.TOOLS, MenuId.GO)
    for menu_id, _ in app.menus:
        if menu_id and menu_id not in skip and is_root_menu_id(app, menu_id):
            yield menu_id
