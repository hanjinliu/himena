from app_model.types import Action, KeyBindingRule, KeyCode, KeyMod, MenuRule
from app_model import Application

ACTIONS: list[Action] = [
    Action(
        id='open',
        title="Open",
        icon="fa6-solid:folder-open",
        callback="default.io:open",
        menus=["file", "toolbar"],
        keybindings=[KeyBindingRule(primary=KeyMod.CtrlCmd | KeyCode.KeyO)],
    ),
    Action(
        id='close',
        title="Close",
        icon="fa-solid:window-close",
        callback="default.window:close",
        menus=["file"],
        keybindings=[KeyBindingRule(primary=KeyMod.CtrlCmd | KeyCode.KeyW)],
    ),
]
