from app_model.types import (
    KeyBindingRule,
    KeyCode,
    KeyMod,
)
from royalapp.consts import MenuId
from royalapp.widgets import MainWindow
from royalapp._app_model.actions._registry import ACTIONS

CMD_GROUP = "command-palette"


@ACTIONS.append_from_fn(
    id="show-command-palette",
    title="Command palette",
    icon="material-symbols:palette-outline",
    menus=[
        {"id": MenuId.TOOLS, "group": CMD_GROUP},
        {"id": MenuId.TOOLBAR, "group": CMD_GROUP},
    ],
    keybindings=[KeyBindingRule(primary=KeyMod.CtrlCmd | KeyMod.Shift | KeyCode.KeyP)],
)
def show_command_palette(ui: MainWindow) -> None:
    ui._backend_main_window._show_command_palette("general")


@ACTIONS.append_from_fn(
    id="go-to-window",
    title="Go to window",
    icon="gg:enter",
    menus=[
        {"id": MenuId.TOOLS, "group": CMD_GROUP},
        {"id": MenuId.TOOLBAR, "group": CMD_GROUP},
    ],
    keybindings=[KeyBindingRule(primary=KeyMod.CtrlCmd | KeyCode.KeyG)],
)
def go_to_window(ui: MainWindow) -> None:
    ui._backend_main_window._show_command_palette("goto")
