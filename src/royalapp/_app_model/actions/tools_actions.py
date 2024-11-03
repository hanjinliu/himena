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


def go_to_window(ui: MainWindow) -> None:
    ui._backend_main_window._show_command_palette("goto")


_CtrlShift = KeyMod.CtrlCmd | KeyMod.Shift

CMD_GROUP = "command-palette"

ACTIONS = [
    Action(
        id="show-command-palette",
        title="Command palette",
        icon="material-symbols:palette-outline",
        callback=show_command_palette,
        menus=[
            {"id": MenuId.TOOLS, "group": CMD_GROUP},
            {"id": MenuId.TOOLBAR, "group": CMD_GROUP},
        ],
        keybindings=[KeyBindingRule(primary=_CtrlShift | KeyCode.KeyP)],
        icon_visible_in_menu=False,
    ),
    Action(
        id="go-to-window",
        title="Go to window",
        tooltip="Go to any existing window",
        icon="gg:enter",
        callback=go_to_window,
        menus=[
            {"id": MenuId.TOOLS, "group": CMD_GROUP},
            {"id": MenuId.TOOLBAR, "group": CMD_GROUP},
        ],
        keybindings=[KeyBindingRule(primary=KeyMod.CtrlCmd | KeyCode.KeyG)],
        icon_visible_in_menu=False,
    ),
]
