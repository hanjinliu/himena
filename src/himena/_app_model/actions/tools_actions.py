from app_model.types import KeyBindingRule, KeyCode, KeyMod
from himena.consts import MenuId
from himena.widgets import MainWindow
from himena._app_model.actions._registry import ACTIONS
from himena._app_model._context import AppContext as _ctx


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
    recording=False,
)
def show_command_palette(ui: MainWindow) -> None:
    """Open the command palette."""
    ui._backend_main_window._show_command_palette("general")


@ACTIONS.append_from_fn(
    id="go-to-window",
    title="Go to window ...",
    menus=[{"id": MenuId.TOOLS, "group": CMD_GROUP}],
    enablement=_ctx.num_tabs > 0,
    keybindings=[KeyBindingRule(primary=KeyMod.CtrlCmd | KeyCode.KeyG)],
    recording=False,
)
def go_to_window(ui: MainWindow) -> None:
    """Go to an existing window."""
    ui._backend_main_window._show_command_palette("goto")


@ACTIONS.append_from_fn(
    id="repeat-command",
    title="Repeat last command",
    menus=[{"id": MenuId.TOOLS, "group": CMD_GROUP}],
    keybindings=[KeyBindingRule(primary=KeyMod.CtrlCmd | KeyCode.KeyR)],
    recording=False,
)
def repeat_last_command(ui: MainWindow) -> None:
    """Repeat the command that was executed last."""
    if id := ui._history_command.get_from_last(1):
        if action := ui.model_app._registered_actions.get(id):
            ctx = ui._ctx_keys.dict()
            if action.enablement is None or action.enablement.eval(ctx):
                ui.exec_action(id)
