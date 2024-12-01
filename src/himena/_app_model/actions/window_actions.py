import logging
import warnings
from app_model.types import (
    KeyCode,
    KeyMod,
    KeyChord,
    StandardKeyBinding,
)
from himena._descriptors import SaveToPath, NoNeedToSave
from himena.consts import MenuId
from himena.widgets import MainWindow
from himena.types import (
    ClipboardDataModel,
    Parametric,
    WindowState,
    WidgetDataModel,
)
from himena._app_model._context import AppContext as _ctx
from himena._app_model.actions._registry import ACTIONS, SUBMENUS
from himena import _utils, _providers
from himena.exceptions import Cancelled

_LOGGER = logging.getLogger(__name__)

EDIT_GROUP = "00_edit"
STATE_GROUP = "01_state"
MOVE_GROUP = "02_move"
ZOOM_GROUP = "10_zoom"
EXIT_GROUP = "99_exit"
_CtrlK = KeyMod.CtrlCmd | KeyCode.KeyK
_CtrlShift = KeyMod.CtrlCmd | KeyMod.Shift


@ACTIONS.append_from_fn(
    id="close-window",
    title="Close window",
    icon="material-symbols:tab-close-outline",
    menus=[
        {"id": MenuId.WINDOW, "group": EXIT_GROUP},
    ],
    keybindings=[StandardKeyBinding.Close],
    enablement=_ctx.num_sub_windows > 0,
)
def close_current_window(ui: MainWindow) -> None:
    """Close the selected sub-window."""
    i_tab = ui.tabs.current_index
    if i_tab is None:
        raise Cancelled
    tab = ui.tabs[i_tab]
    i_window = tab.current_index
    if i_window is None:
        raise Cancelled
    _LOGGER.info(f"Closing window {i_window} in tab {i_tab}")
    tab[i_window]._close_me(ui, ui._instructions.confirm)


@ACTIONS.append_from_fn(
    id="open-last-closed-window",
    title="Open last closed window",
    menus=[{"id": MenuId.WINDOW, "group": EXIT_GROUP}],
    keybindings=[{"primary": _CtrlShift | KeyCode.KeyT}],
)
def open_last_closed_window(ui: MainWindow) -> WidgetDataModel:
    """Open the last closed window."""
    if last := ui._history_closed.pop_last():
        path, plugin = last
        store = _providers.ReaderProviderStore().instance()
        model = store.run(path=path, plugin=plugin)
        return model
    warnings.warn("No window to reopen", UserWarning, stacklevel=2)
    raise Cancelled


@ACTIONS.append_from_fn(
    id="duplicate-window",
    title="Duplicate window",
    enablement=_ctx.is_active_window_exportable,
    menus=[{"id": MenuId.WINDOW, "group": EDIT_GROUP}],
    keybindings=[{"primary": KeyChord(_CtrlK, _CtrlShift | KeyCode.KeyD)}],
    need_function_callback=True,
)
def duplicate_window(model: WidgetDataModel) -> WidgetDataModel:
    """Duplicate the selected sub-window."""
    update = {"save_behavior_override": NoNeedToSave()}
    if model.title is not None:
        update["title"] = _utils.add_title_suffix(model.title)
    return model.model_copy(update=update)


@ACTIONS.append_from_fn(
    id="view-data-in",
    title="View data in ...",
    enablement=_ctx.is_active_window_exportable,
    menus=[{"id": MenuId.WINDOW, "group": EDIT_GROUP}],
    keybindings=[{"primary": KeyMod.Alt | KeyCode.KeyV}],
    need_function_callback=True,
)
def view_data_in(ui: MainWindow, model: WidgetDataModel) -> Parametric:
    """View the internal data of the selected sub-window in other registered widget."""
    from himena.plugins import configure_gui

    choices: list[tuple[str, str]] = []
    widget_classes, _ = ui._backend_main_window._list_widget_class(model.type)
    for _, cls, _ in widget_classes:
        name = f"{cls.__module__}.{cls.__name__}"
        display_name = _utils.get_display_name(cls)
        choices.append((display_name, name))

    @configure_gui(
        plugin={
            "choices": choices,
            "widget_type": "RadioButtons",
            "value": choices[0][1],
        },
        title="Choose a widget ...",
        show_parameter_labels=False,
    )
    def choose_a_widget(plugin: str) -> WidgetDataModel:
        return model.with_open_plugin(plugin, save_behavior_override=NoNeedToSave())

    return choose_a_widget


@ACTIONS.append_from_fn(
    id="rename-window",
    title="Rename window",
    menus=[
        {"id": MenuId.WINDOW, "group": EDIT_GROUP},
    ],
    enablement=_ctx.num_sub_windows > 0,
    keybindings=[{"primary": KeyChord(_CtrlK, KeyCode.F2)}],
)
def rename_window(ui: MainWindow) -> None:
    """Rename the title of the window."""
    i_tab = ui.tabs.current_index
    if i_tab is None:
        return None
    if (i_win := ui._backend_main_window._current_sub_window_index()) is not None:
        ui._backend_main_window._rename_window_at(i_tab, i_win)


@ACTIONS.append_from_fn(
    id="copy-path-to-clipboard",
    title="Copy path to clipboard",
    menus=[{"id": MenuId.WINDOW, "group": EDIT_GROUP}],
    enablement=_ctx.num_sub_windows > 0,
    keybindings=[{"primary": KeyChord(_CtrlK, _CtrlShift | KeyCode.KeyC)}],
)
def copy_path_to_clipboard(ui: MainWindow) -> ClipboardDataModel:
    """Copy the path of the current window to the clipboard."""
    if window := ui.current_window:
        if isinstance(sv := window.save_behavior, SaveToPath):
            return ClipboardDataModel(text=str(sv.path))
        else:
            warnings.warn(
                "Window does not have the source path.", UserWarning, stacklevel=2
            )
    else:
        warnings.warn("No window is focused.", UserWarning, stacklevel=2)
    raise Cancelled


@ACTIONS.append_from_fn(
    id="copy-data-to-clipboard",
    title="Copy data to clipboard",
    menus=[
        {"id": MenuId.WINDOW, "group": EDIT_GROUP},
    ],
    enablement=(_ctx.num_sub_windows > 0) & _ctx.is_active_window_exportable,
    keybindings=[{"primary": KeyChord(_CtrlK, KeyMod.CtrlCmd | KeyCode.KeyC)}],
)
def copy_data_to_clipboard(ui: MainWindow) -> ClipboardDataModel:
    """Copy the data of the current window to the clipboard."""
    if window := ui.current_window:
        return window.to_model().to_clipboard_data_model()
    warnings.warn("No window is focused.", UserWarning, stacklevel=2)
    raise Cancelled


@ACTIONS.append_from_fn(
    id="minimize-window",
    title="Minimize window",
    menus=[{"id": MenuId.WINDOW_RESIZE, "group": STATE_GROUP}],
    keybindings=[{"primary": KeyChord(_CtrlK, KeyMod.CtrlCmd | KeyCode.DownArrow)}],
    enablement=_ctx.num_sub_windows > 0,
)
def minimize_current_window(ui: MainWindow) -> None:
    """Minimize the window"""
    if window := ui.current_window:
        window.state = WindowState.MIN


@ACTIONS.append_from_fn(
    id="maximize-window",
    title="Maximize window",
    menus=[{"id": MenuId.WINDOW_RESIZE, "group": STATE_GROUP}],
    enablement=_ctx.num_sub_windows > 0,
    keybindings=[{"primary": KeyChord(_CtrlK, KeyMod.CtrlCmd | KeyCode.UpArrow)}],
)
def maximize_current_window(ui: MainWindow) -> None:
    if window := ui.current_window:
        window.state = WindowState.MAX


@ACTIONS.append_from_fn(
    id="toggle-full-screen",
    title="Toggle full screen",
    menus=[{"id": MenuId.WINDOW_RESIZE, "group": STATE_GROUP}],
    keybindings=[{"primary": KeyCode.F11}],
    enablement=_ctx.num_sub_windows > 0,
)
def toggle_full_screen(ui: MainWindow) -> None:
    if window := ui.current_window:
        if window.state is WindowState.MAX:
            window.state = WindowState.NORMAL
        else:
            window.state = WindowState.MAX


@ACTIONS.append_from_fn(
    id="unset-anchor",
    title="Unanchor window",
    menus=[MenuId.WINDOW_ANCHOR],
    enablement=_ctx.num_sub_windows > 0,
)
def unset_anchor(ui: MainWindow) -> None:
    """Unset the anchor of the window if exists."""
    if window := ui.current_window:
        window.anchor = None


@ACTIONS.append_from_fn(
    id="anchor-window-top-left",
    title="Anchor window to top-left corner",
    menus=[MenuId.WINDOW_ANCHOR],
    enablement=_ctx.num_sub_windows > 0,
)
def anchor_at_top_left(ui: MainWindow) -> None:
    """Anchor the window at the top-left corner of the current window position."""
    if window := ui.current_window:
        window.anchor = "top-left"


@ACTIONS.append_from_fn(
    id="anchor-window-top-right",
    title="Anchor window to top-right corner",
    menus=[MenuId.WINDOW_ANCHOR],
    enablement=_ctx.num_sub_windows > 0,
)
def anchor_at_top_right(ui: MainWindow) -> None:
    """Anchor the window at the top-right corner of the current window position."""
    if window := ui.current_window:
        window.anchor = "top-right"


@ACTIONS.append_from_fn(
    id="anchor-window-bottom-left",
    title="Anchor window to bottom-left corner",
    menus=[MenuId.WINDOW_ANCHOR],
    enablement=_ctx.num_sub_windows > 0,
)
def anchor_at_bottom_left(ui: MainWindow) -> None:
    """Anchor the window at the bottom-left corner of the current window position."""
    if window := ui.current_window:
        window.anchor = "bottom-left"


@ACTIONS.append_from_fn(
    id="anchor-window-bottom-right",
    title="Anchor window to bottom-right corner",
    menus=[MenuId.WINDOW_ANCHOR],
    enablement=_ctx.num_sub_windows > 0,
)
def anchor_at_bottom_right(ui: MainWindow) -> None:
    """Anchor the window at the bottom-right corner of the current window position."""
    if window := ui.current_window:
        window.anchor = "bottom-right"


@ACTIONS.append_from_fn(
    id="window-expand",
    title="Expand (+20%)",
    enablement=_ctx.num_sub_windows > 0,
    menus=[{"id": MenuId.WINDOW_RESIZE, "group": ZOOM_GROUP}],
    keybindings=[StandardKeyBinding.ZoomIn],
)
def window_expand(ui: MainWindow) -> None:
    """Expand (increase the size of) the current window."""
    if window := ui.current_window:
        window._set_rect(window.rect.resize_relative(1.2, 1.2))


@ACTIONS.append_from_fn(
    id="window-shrink",
    title="Shrink (-20%)",
    enablement=_ctx.num_sub_windows > 0,
    menus=[{"id": MenuId.WINDOW_RESIZE, "group": ZOOM_GROUP}],
    keybindings=[StandardKeyBinding.ZoomOut],
)
def window_shrink(ui: MainWindow) -> None:
    """Shrink (reduce the size of) the current window."""
    if window := ui.current_window:
        window._set_rect(window.rect.resize_relative(1 / 1.2, 1 / 1.2))


@ACTIONS.append_from_fn(
    id="full-screen-in-new-tab",
    title="Full screen in new tab",
    enablement=_ctx.num_sub_windows > 0,
    menus=[{"id": MenuId.WINDOW, "group": EDIT_GROUP}],
)
def full_screen_in_new_tab(ui: MainWindow) -> None:
    """Move the selected sub-window to a new tab and make it full screen."""
    if win := ui.current_window:
        ui.add_tab(win.title)
        index_new = len(ui.tabs) - 1
        ui.move_window(win, index_new)
        win.state = WindowState.FULL
        ui.tabs.current_index = index_new


_CtrlAlt = KeyMod.CtrlCmd | KeyMod.Alt


@ACTIONS.append_from_fn(
    id="align-window-left",
    title="Align window to left",
    enablement=_ctx.num_sub_windows > 0,
    menus=[MenuId.WINDOW_ALIGN],
    keybindings=[{"primary": _CtrlAlt | KeyCode.LeftArrow}],
)
def align_window_left(ui: MainWindow) -> None:
    """Align the window to the left edge of the tab area."""
    if window := ui.current_window:
        window._set_rect(window.rect.align_left(ui.area_size))


@ACTIONS.append_from_fn(
    id="align-window-right",
    title="Align window to right",
    enablement=_ctx.num_sub_windows > 0,
    menus=[MenuId.WINDOW_ALIGN],
    keybindings=[{"primary": _CtrlAlt | KeyCode.RightArrow}],
)
def align_window_right(ui: MainWindow) -> None:
    """Align the window to the right edge of the tab area."""
    if window := ui.current_window:
        window._set_rect(window.rect.align_right(ui.area_size))


@ACTIONS.append_from_fn(
    id="align-window-top",
    title="Align window to top",
    enablement=_ctx.num_sub_windows > 0,
    menus=[MenuId.WINDOW_ALIGN],
    keybindings=[{"primary": _CtrlAlt | KeyCode.UpArrow}],
)
def align_window_top(ui: MainWindow) -> None:
    """Align the window to the top edge of the tab area."""
    if window := ui.current_window:
        window._set_rect(window.rect.align_top(ui.area_size))


@ACTIONS.append_from_fn(
    id="align-window-bottom",
    title="Align window to bottom",
    enablement=_ctx.num_sub_windows > 0,
    menus=[MenuId.WINDOW_ALIGN],
    keybindings=[{"primary": _CtrlAlt | KeyCode.DownArrow}],
)
def align_window_bottom(ui: MainWindow) -> None:
    """Align the window to the bottom edge of the tab area."""
    if window := ui.current_window:
        window._set_rect(window.rect.align_bottom(ui.area_size))


@ACTIONS.append_from_fn(
    id="align-window-center",
    title="Align window to center",
    enablement=_ctx.num_sub_windows > 0,
    menus=[MenuId.WINDOW_ALIGN],
    keybindings=[{"primary": _CtrlAlt | KeyCode.Space}],
)
def align_window_center(ui: MainWindow) -> None:
    """Align the window to the center of the tab area."""
    if window := ui.current_window:
        window._set_rect(window.rect.align_center(ui.area_size))


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
        title=f"{n}{th} window",
        enablement=_ctx.num_sub_windows > n,
        menus=[MenuId.WINDOW_NTH],
        keybindings=[{"primary": KeyMod.Alt | keycode}],
    )(make_func(n))

SUBMENUS.append_from(
    id=MenuId.WINDOW,
    submenu=MenuId.WINDOW_RESIZE,
    title="Resize",
    enablement=_ctx.num_sub_windows > 0,
    group=MOVE_GROUP,
)
SUBMENUS.append_from(
    id=MenuId.WINDOW,
    submenu=MenuId.WINDOW_ALIGN,
    title="Align",
    enablement=_ctx.num_sub_windows > 0,
    group=MOVE_GROUP,
)
SUBMENUS.append_from(
    id=MenuId.WINDOW,
    submenu=MenuId.WINDOW_ANCHOR,
    title="Anchor",
    enablement=_ctx.num_sub_windows > 0,
    group=MOVE_GROUP,
)
SUBMENUS.append_from(
    id=MenuId.WINDOW,
    submenu=MenuId.WINDOW_NTH,
    title="Jump to",
    enablement=_ctx.num_sub_windows > 0,
    group=MOVE_GROUP,
)
