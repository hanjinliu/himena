from app_model.types import (
    KeyBindingRule,
    KeyCode,
    KeyMod,
)
from himena.consts import MenuId
from himena.widgets import MainWindow
from himena._app_model._context import AppContext as _ctx
from himena._app_model.actions._registry import ACTIONS

GO_TO_GROUP = "10_go-to"
JUMP_TO_GROUP = "11_jump-to"


# Jump to the nth window
def make_func(n: int):
    def jump_to_nth_window(ui: MainWindow) -> None:
        if (area := ui.tabs.current()) and len(area) > n:
            area.current_index = n

    jump_to_nth_window.__name__ = f"jump_to_window_{n}"
    jump_to_nth_window.__doc__ = f"Jump to the {n}-th window in the current tab."
    jump_to_nth_window.__qualname__ = f"jump_to_window_{n}"
    jump_to_nth_window.__module__ = make_func.__module__
    return jump_to_nth_window


for n in range(10):
    th: str = "st" if n == 1 else "nd" if n == 2 else "rd" if n == 3 else "th"
    keycode = getattr(KeyCode, f"Digit{n}")
    ACTIONS.append_from_fn(
        id=f"jump-to-window-{n}",
        title=f"Jump To {n}{th} Window",
        enablement=_ctx.num_sub_windows > n,
        menus=[{"id": MenuId.GO, "group": JUMP_TO_GROUP}],
        keybindings=[{"primary": KeyMod.Alt | keycode}],
    )(make_func(n))


@ACTIONS.append_from_fn(
    id="go-to-previous-window",
    title="Go To Previous Window",
    menus=[MenuId.GO],
    enablement=(_ctx.num_tabs > 0) & (_ctx.num_sub_windows > 1),
    keybindings=[KeyBindingRule(primary=KeyMod.CtrlCmd | KeyCode.Home)],
    recording=False,
)
def go_to_previous_window(ui: MainWindow) -> None:
    """Go to the previous window."""
    if (area := ui.tabs.current()) and len(area) > 1:
        area.current_index = (area.current_index - 1) % len(area)


@ACTIONS.append_from_fn(
    id="go-to-next-window",
    title="Go To Next Window",
    menus=[MenuId.GO],
    enablement=(_ctx.num_tabs > 0) & (_ctx.num_sub_windows > 1),
    keybindings=[KeyBindingRule(primary=KeyMod.CtrlCmd | KeyCode.End)],
    recording=False,
)
def go_to_next_window(ui: MainWindow) -> None:
    """Go to the next window."""
    if (area := ui.tabs.current()) and len(area) > 1:
        area.current_index = (area.current_index + 1) % len(area)


@ACTIONS.append_from_fn(
    id="go-to-window",
    title="Go To Window ...",
    menus=[MenuId.GO],
    enablement=_ctx.num_tabs > 0,
    keybindings=[KeyBindingRule(primary=KeyMod.CtrlCmd | KeyCode.KeyG)],
    recording=False,
)
def go_to_window(ui: MainWindow) -> None:
    """Go to an existing window."""
    ui._backend_main_window._show_command_palette("goto")
