import logging
from app_model.types import (
    Action,
    KeyBindingRule,
    KeyCode,
    KeyMod,
    SubmenuItem,
    KeyChord,
)
from royalapp._descriptors import ConverterMethod
from royalapp.consts import MenuId
from royalapp.widgets import MainWindow
from royalapp.types import SubWindowState, WidgetDataModel
from royalapp._app_model._context import AppContext as _ctx

_LOGGER = logging.getLogger(__name__)


def close_current_window(ui: MainWindow) -> None:
    """Close the selected sub-window."""
    i_tab = ui.tabs.current_index()
    if i_tab is None:
        return None
    i_window = ui.tabs[i_tab].current_index()
    if i_window is None:
        return None
    win = ui.tabs[i_tab][i_window]
    if win.is_modified:
        if not ui.exec_confirmation_dialog(f"Close {win.title} without saving?"):
            return None
    _LOGGER.info(f"Closing window {i_window} in tab {i_tab}")
    del ui.tabs[i_tab][i_window]


def close_all_windows_in_tab(ui: MainWindow) -> None:
    """Close all sub-windows in the current tab."""
    if area := ui.tabs.current():
        win_modified = [win for win in area if win.is_modified]
        if len(win_modified) > 0:
            _modified_msg = "\n".join([f"- {win.title}" for win in win_modified])
            if not ui.exec_confirmation_dialog(
                f"Some windows are modified:\n{_modified_msg}\nClose without saving?"
            ):
                return None
        area.clear()


def duplicate_window(model: WidgetDataModel) -> WidgetDataModel:
    """Duplicate the selected sub-window."""
    if model.title is not None:
        model.title += " (copy)"
    if (method := model.method) is not None:
        model.method = ConverterMethod(original=method, action_id="duplicate-window")
    return model


def rename_window(ui: MainWindow) -> None:
    i_tab = ui.tabs.current_index()
    if i_tab is None:
        return None
    if (i_win := ui._backend_main_window._current_sub_window_index()) is not None:
        ui._backend_main_window._rename_window_at(i_tab, i_win)


def minimize_current_window(ui: MainWindow) -> None:
    if window := ui.current_window:
        window.state = SubWindowState.MIN


def maximize_current_window(ui: MainWindow) -> None:
    if window := ui.current_window:
        window.state = SubWindowState.MAX


def toggle_full_screen(ui: MainWindow) -> None:
    if window := ui.current_window:
        if window.state is SubWindowState.MAX:
            window.state = SubWindowState.NORMAL
        else:
            window.state = SubWindowState.MAX


def unset_anchor(ui: MainWindow) -> None:
    if window := ui.current_window:
        window.anchor = None


def anchor_at_top_left(ui: MainWindow) -> None:
    if window := ui.current_window:
        window.anchor = "top-left"


def anchor_at_top_right(ui: MainWindow) -> None:
    if window := ui.current_window:
        window.anchor = "top-right"


def anchor_at_bottom_left(ui: MainWindow) -> None:
    if window := ui.current_window:
        window.anchor = "bottom-left"


def anchor_at_bottom_right(ui: MainWindow) -> None:
    if window := ui.current_window:
        window.anchor = "bottom-right"


def minimize_others(ui: MainWindow):
    """Minimize all sub-windows except the current one."""
    if area := ui.tabs.current():
        cur_window = area.current()
        for window in area:
            if cur_window is window:
                continue
            window.state = SubWindowState.MIN


def show_all_windows(ui: MainWindow):
    """Show all sub-windows in the current tab."""
    if area := ui.tabs.current():
        for window in area:
            if window.state is SubWindowState.MIN:
                window.state = SubWindowState.NORMAL


def full_screen_in_new_tab(ui: MainWindow) -> None:
    """Move the selected sub-window to a new tab and make it full screen."""
    if area := ui.tabs.current():
        index = area.current_index()
        if index is None:
            return
        window = area.pop(index)
        ui.add_tab(window.title)
        new_window = ui.tabs[-1].add_widget(window.widget, title=window.title)
        new_window.state = SubWindowState.FULL


def align_window_left(ui: MainWindow) -> None:
    if window := ui.current_window:
        window.window_rect = window.window_rect.align_left()


def align_window_right(ui: MainWindow) -> None:
    if window := ui.current_window:
        window.window_rect = window.window_rect.align_right(ui.area_size)


def align_window_top(ui: MainWindow) -> None:
    if window := ui.current_window:
        window.window_rect = window.window_rect.align_top(ui.area_size)


def align_window_bottom(ui: MainWindow) -> None:
    if window := ui.current_window:
        window.window_rect = window.window_rect.align_bottom(ui.area_size)


def align_window_center(ui: MainWindow) -> None:
    if window := ui.current_window:
        window.window_rect = window.window_rect.align_center(ui.area_size)


def tile_windows(ui: MainWindow) -> None:
    if area := ui.tabs.current():
        area.tile_windows()


_CtrlAlt = KeyMod.CtrlCmd | KeyMod.Alt
_CtrlShift = KeyMod.CtrlCmd | KeyMod.Shift
_CtrlK = KeyMod.CtrlCmd | KeyCode.KeyK

EDIT_GROUP = "00_edit"
STATE_GROUP = "01_state"
MOVE_GROUP = "02_move"
EXIT_GROUP = "99_exit"

SUBMENUS = [
    (
        MenuId.WINDOW,
        SubmenuItem(
            submenu=MenuId.WINDOW_ALIGN,
            title="Align",
            enablement=_ctx.has_sub_windows,
            group=MOVE_GROUP,
        ),
    ),
    (
        MenuId.WINDOW,
        SubmenuItem(
            submenu=MenuId.WINDOW_ANCHOR,
            title="Anchor",
            enablement=_ctx.has_sub_windows,
            group=MOVE_GROUP,
        ),
    ),
    (
        MenuId.WINDOW_TITLE_BAR,
        SubmenuItem(
            submenu=MenuId.WINDOW_TITLE_BAR_ALIGN,
            title="Align",
            enablement=_ctx.has_sub_windows,
            group=MOVE_GROUP,
        ),
    ),
    (
        MenuId.WINDOW_TITLE_BAR,
        SubmenuItem(
            submenu=MenuId.WINDOW_TITLE_BAR_ANCHOR,
            title="Anchor",
            enablement=_ctx.has_sub_windows,
            group=MOVE_GROUP,
        ),
    ),
]

ACTIONS = [
    Action(
        id="duplicate-window",
        title="Duplicate current window",
        callback=duplicate_window,
        menus=[
            {"id": MenuId.WINDOW, "group": EDIT_GROUP},
            {"id": MenuId.WINDOW_TITLE_BAR, "group": EDIT_GROUP},
        ],
        enablement=_ctx.is_active_window_exportable,
        keybindings=[KeyBindingRule(primary=_CtrlShift | KeyCode.KeyD)],
        icon_visible_in_menu=False,
    ),
    Action(
        id="rename-window",
        title="Rename window",
        callback=rename_window,
        menus=[
            {"id": MenuId.WINDOW, "group": EDIT_GROUP},
            {"id": MenuId.WINDOW_TITLE_BAR, "group": EDIT_GROUP},
        ],
        enablement=_ctx.has_sub_windows,
        keybindings=[
            KeyBindingRule(primary=KeyChord(_CtrlK, KeyCode.F2)),
        ],
        icon_visible_in_menu=False,
    ),
    Action(
        id="minimize-other-windows",
        title="Minimize other windows",
        callback=minimize_others,
        menus=[
            {"id": MenuId.WINDOW, "group": STATE_GROUP},
            {"id": MenuId.WINDOW_TITLE_BAR, "group": STATE_GROUP},
        ],
        enablement=_ctx.has_sub_windows,
        icon_visible_in_menu=False,
    ),
    Action(
        id="full-screen-in-new-tab",
        title="Full screen in new tab",
        callback=full_screen_in_new_tab,
        menus=[
            {"id": MenuId.WINDOW, "group": STATE_GROUP},
            {"id": MenuId.WINDOW_TITLE_BAR, "group": STATE_GROUP},
        ],
        enablement=_ctx.has_sub_windows,
        icon_visible_in_menu=False,
    ),
    Action(
        id="show-all-windows",
        title="Show all windows",
        callback=show_all_windows,
        menus=[{"id": MenuId.WINDOW, "group": STATE_GROUP}],
        enablement=_ctx.has_sub_windows,
        icon_visible_in_menu=False,
    ),
    Action(
        id="minimize-window",
        title="Minimize window",
        callback=minimize_current_window,
        menus=[
            {"id": MenuId.WINDOW, "group": STATE_GROUP},
            {"id": MenuId.WINDOW_TITLE_BAR, "group": STATE_GROUP},
        ],
        enablement=_ctx.has_sub_windows,
        icon_visible_in_menu=False,
    ),
    Action(
        id="maximize-window",
        title="Maximize window",
        callback=maximize_current_window,
        menus=[
            {"id": MenuId.WINDOW, "group": STATE_GROUP},
            {"id": MenuId.WINDOW_TITLE_BAR, "group": STATE_GROUP},
        ],
        enablement=_ctx.has_sub_windows,
        icon_visible_in_menu=False,
    ),
    Action(
        id="toggle-full-screen",
        title="Toggle full screen",
        callback=toggle_full_screen,
        menus=[
            {"id": MenuId.WINDOW, "group": STATE_GROUP},
            {"id": MenuId.WINDOW_TITLE_BAR, "group": STATE_GROUP},
        ],
        enablement=_ctx.has_sub_windows,
        icon_visible_in_menu=False,
    ),
    Action(
        id="tile-windows",
        title="Tile windows",
        callback=tile_windows,
        menus=[MenuId.WINDOW_ALIGN],
        enablement=_ctx.has_sub_windows,
        icon_visible_in_menu=False,
    ),
    Action(
        id="align-window-left",
        title="Align window to left",
        callback=align_window_left,
        menus=[MenuId.WINDOW_ALIGN, MenuId.WINDOW_TITLE_BAR_ALIGN],
        enablement=_ctx.has_sub_windows,
        keybindings=[KeyBindingRule(primary=_CtrlAlt | KeyCode.LeftArrow)],
        icon_visible_in_menu=False,
    ),
    Action(
        id="align-window-right",
        title="Align window to right",
        callback=align_window_right,
        menus=[MenuId.WINDOW_ALIGN, MenuId.WINDOW_TITLE_BAR_ALIGN],
        enablement=_ctx.has_sub_windows,
        keybindings=[KeyBindingRule(primary=_CtrlAlt | KeyCode.RightArrow)],
        icon_visible_in_menu=False,
    ),
    Action(
        id="align-window-top",
        title="Align window to top",
        callback=align_window_top,
        menus=[MenuId.WINDOW_ALIGN, MenuId.WINDOW_TITLE_BAR_ALIGN],
        enablement=_ctx.has_sub_windows,
        keybindings=[KeyBindingRule(primary=_CtrlAlt | KeyCode.UpArrow)],
        icon_visible_in_menu=False,
    ),
    Action(
        id="align-window-bottom",
        title="Align window to bottom",
        callback=align_window_bottom,
        menus=[MenuId.WINDOW_ALIGN, MenuId.WINDOW_TITLE_BAR_ALIGN],
        enablement=_ctx.has_sub_windows,
        keybindings=[KeyBindingRule(primary=_CtrlAlt | KeyCode.DownArrow)],
        icon_visible_in_menu=False,
    ),
    Action(
        id="align-window-center",
        title="Align window to center",
        callback=align_window_center,
        menus=[MenuId.WINDOW_ALIGN, MenuId.WINDOW_TITLE_BAR_ALIGN],
        enablement=_ctx.has_sub_windows,
        keybindings=[KeyBindingRule(primary=_CtrlAlt | KeyCode.Space)],
        icon_visible_in_menu=False,
    ),
    Action(
        id="unanchor-window",
        title="Unanchor window",
        callback=unset_anchor,
        menus=[MenuId.WINDOW_ANCHOR, MenuId.WINDOW_TITLE_BAR_ANCHOR],
        enablement=_ctx.has_sub_windows,
        icon_visible_in_menu=False,
    ),
    Action(
        id="anchor-window-top-left",
        title="Anchor window to top-left corner",
        callback=anchor_at_top_left,
        menus=[MenuId.WINDOW_ALIGN, MenuId.WINDOW_TITLE_BAR_ANCHOR],
        enablement=_ctx.has_sub_windows,
        icon_visible_in_menu=False,
    ),
    Action(
        id="anchor-window-top-right",
        title="Anchor window to top-right corner",
        callback=anchor_at_top_right,
        menus=[MenuId.WINDOW_ALIGN, MenuId.WINDOW_TITLE_BAR_ANCHOR],
        enablement=_ctx.has_sub_windows,
        icon_visible_in_menu=False,
    ),
    Action(
        id="anchor-window-bottom-left",
        title="Anchor window to bottom-left corner",
        callback=anchor_at_bottom_left,
        menus=[MenuId.WINDOW_ALIGN, MenuId.WINDOW_TITLE_BAR_ANCHOR],
        enablement=_ctx.has_sub_windows,
        icon_visible_in_menu=False,
    ),
    Action(
        id="anchor-window-bottom-right",
        title="Anchor window to bottom-right corner",
        callback=anchor_at_bottom_right,
        menus=[MenuId.WINDOW_ALIGN, MenuId.WINDOW_TITLE_BAR_ANCHOR],
        enablement=_ctx.has_sub_windows,
        icon_visible_in_menu=False,
    ),
    Action(
        id="close-window",
        title="Close window",
        icon="material-symbols:tab-close-outline",
        callback=close_current_window,
        menus=[
            {"id": MenuId.WINDOW, "group": EXIT_GROUP},
            {"id": MenuId.WINDOW_TITLE_BAR, "group": EXIT_GROUP},
        ],
        keybindings=[KeyBindingRule(primary=KeyMod.CtrlCmd | KeyCode.KeyW)],
        enablement=_ctx.has_sub_windows,
        icon_visible_in_menu=False,
    ),
    Action(
        id="close-all-window",
        title="Close all windows in tab",
        callback=close_all_windows_in_tab,
        menus=[{"id": MenuId.WINDOW, "group": EXIT_GROUP}],
        enablement=_ctx.has_sub_windows,
        icon_visible_in_menu=False,
    ),
]
