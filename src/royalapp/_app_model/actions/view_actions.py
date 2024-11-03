from app_model.types import (
    Action,
    KeyBindingRule,
    KeyCode,
    KeyMod,
)
from royalapp.consts import MenuId
from royalapp.widgets import MainWindow


def show_command_palette(ui: MainWindow) -> None:
    ui._backend_main_window._show_command_palette("general")


_CtrlShift = KeyMod.CtrlCmd | KeyMod.Shift

ACTIONS = [
    Action(
        id="show-command-palette",
        title="Show command palette",
        callback=show_command_palette,
        menus=[MenuId.VIEW],
        keybindings=[KeyBindingRule(primary=_CtrlShift | KeyCode.KeyP)],
        icon_visible_in_menu=False,
    ),
]
