from app_model.types import (
    KeyBindingRule,
    KeyCode,
    KeyMod,
    StandardKeyBinding,
)
from himena._utils import OrderedSet
from himena.consts import MenuId
from himena.plugins._signature import configure_gui
from himena.widgets import MainWindow
from himena.types import (
    Parametric,
    WindowState,
)
from himena._app_model._context import AppContext as _ctx
from himena._app_model.actions._registry import ACTIONS
from himena.widgets._wrapper import SubWindow

WINDOW_GROUP = "00_window"


@ACTIONS.append_from_fn(
    id="new-tab",
    title="New Tab",
    menus=[MenuId.VIEW],
    keybindings=[StandardKeyBinding.AddTab],
)
def new_tab(ui: MainWindow) -> None:
    """Create a new tab."""
    ui.add_tab()


@ACTIONS.append_from_fn(
    id="close-tab",
    title="Close Tab",
    enablement=_ctx.num_tabs > 0,
    menus=[MenuId.VIEW],
    keybindings=[KeyBindingRule(primary=KeyMod.CtrlCmd | KeyMod.Shift | KeyCode.KeyW)],
)
def close_current_tab(ui: MainWindow) -> None:
    """Close the current tab."""
    idx = ui._backend_main_window._current_tab_index()
    if idx is None:
        return
    win_modified = [win for win in ui.tabs[idx] if win.is_modified]
    if len(win_modified) > 0:
        _modified_msg = "\n".join([f"- {win.title}" for win in win_modified])
        if not ui.exec_confirmation_dialog(
            f"Some windows in this tab are not saved yet:\n{_modified_msg}\n"
            "Close the tab without saving?"
        ):
            return None
    ui.tabs.pop(idx)


@ACTIONS.append_from_fn(
    id="goto-last-tab",
    title="Go to Last Tab",
    enablement=_ctx.num_tabs > 1,
    menus=[MenuId.VIEW],
    keybindings=[KeyBindingRule(primary=KeyMod.CtrlCmd | KeyCode.Tab)],
    recording=False,
)
def goto_last_tab(ui: MainWindow) -> None:
    """Go to the last tab."""
    if (idx := ui._history_tab.get_from_last(2)) is not None:
        ui.tabs.current_index = idx


@ACTIONS.append_from_fn(
    id="merge-tabs",
    title="Merge Tabs ...",
    enablement=_ctx.num_tabs > 1,
    menus=[MenuId.VIEW],
    need_function_callback=True,
)
def merge_tabs(ui: MainWindow) -> Parametric:
    """Select tabs and merge them."""
    if len(ui.tabs) < 2:
        return

    @configure_gui(names={"choices": ui.tabs.names, "widget_type": "Select"})
    def choose_tabs_to_merge(names: list[str]) -> None:
        if len(names) < 2:
            return
        i_tab = ui.tabs.names.index(names[0])
        for name in names[1:]:
            for window in ui.tabs[name]:
                ui.move_window(window, i_tab)
            del ui.tabs[name]
        return None

    return choose_tabs_to_merge


@ACTIONS.append_from_fn(
    id="minimize-other-windows",
    title="Minimize other windows",
    menus=[
        {"id": MenuId.VIEW, "group": WINDOW_GROUP},
    ],
    enablement=(_ctx.num_sub_windows > 1) & _ctx.is_subwindow_focused,
)
def minimize_others(ui: MainWindow):
    """Minimize all sub-windows except the current one."""
    if area := ui.tabs.current():
        if cur_window := area.current():
            for window in area:
                if cur_window is window:
                    continue
                window.state = WindowState.MIN
            return
    raise RuntimeError("No window focused.")


@ACTIONS.append_from_fn(
    id="show-all-windows",
    title="Show all windows",
    menus=[{"id": MenuId.VIEW, "group": WINDOW_GROUP}],
    enablement=_ctx.num_sub_windows > 0,
)
def show_all_windows(ui: MainWindow):
    """Show all sub-windows in the current tab."""
    if area := ui.tabs.current():
        for window in area:
            if window.state is WindowState.MIN:
                window.state = WindowState.NORMAL


@ACTIONS.append_from_fn(
    id="tile-windows",
    title="Tile windows",
    enablement=_ctx.num_sub_windows > 1,
    menus=[{"id": MenuId.VIEW, "group": WINDOW_GROUP}],
)
def tile_windows(ui: MainWindow) -> None:
    """Tile all the windows."""
    if area := ui.tabs.current():
        area.tile_windows()


@ACTIONS.append_from_fn(
    id="collect-windows",
    title="Collect windows from other tabs",
    menus=[{"id": MenuId.VIEW, "group": WINDOW_GROUP}],
    enablement=_ctx.num_tabs > 1,
    need_function_callback=True,
)
def collect_windows(ui: MainWindow) -> Parametric:
    """Collect windows based on their titles."""
    from fnmatch import fnmatch, fnmatchcase

    existing_types = OrderedSet(win.model_type() for win in ui.iter_windows())

    @configure_gui(
        model_type={"choices": list(existing_types), "value": None},
    )
    def run_collect_windows(
        pattern: str = "*",
        case_sensitive: bool = True,
        model_type: str | None = None,
    ) -> None:
        windows_to_move: list[SubWindow] = []
        _match = fnmatchcase if case_sensitive else fnmatch
        target_index = ui.tabs.current_index
        for win in ui.iter_windows():
            if not _match(win.title, pattern):
                continue
            if model_type is None or win.model_type() == model_type:
                windows_to_move.append(win)
        if windows_to_move:
            for win in windows_to_move:
                ui.move_window(win, target_index)
        ui.tabs.current_index = target_index
        return None

    return run_collect_windows


@ACTIONS.append_from_fn(
    id="close-all-windows",
    title="Close all windows in tab",
    menus=[{"id": MenuId.VIEW, "group": WINDOW_GROUP}],
    enablement=_ctx.num_sub_windows > 0,
)
def close_all_windows_in_tab(ui: MainWindow) -> None:
    """Close all sub-windows in the current tab."""
    if area := ui.tabs.current():
        win_modified = [win for win in area if win.is_modified]
        if len(win_modified) > 0 and ui._instructions.confirm:
            _modified_msg = "\n".join([f"- {win.title}" for win in win_modified])
            if not ui.exec_confirmation_dialog(
                f"Some windows are modified:\n{_modified_msg}\nClose without saving?"
            ):
                return None
        area.clear()
    return None
