from __future__ import annotations
from typing import Iterable, TYPE_CHECKING
from app_model import Application
from app_model.types import MenuItem

if TYPE_CHECKING:
    from app_model.types import MenuOrSubmenu, Action


def collect_commands(
    app: Application,
    menu_items: list[MenuOrSubmenu],
    exclude: Iterable[str],
) -> list[Action]:
    commands = []
    for item in menu_items:
        if isinstance(item, MenuItem):
            if item.command.id not in exclude:
                commands.append(item.command)
        else:
            commands.extend(
                collect_commands(app, app.menus.get_menu(item.submenu), exclude)
            )
    return commands
