import logging
from pathlib import Path
import sys
import warnings
from app_model.types import (
    Action,
    ToggleRule,
    KeyCode,
    KeyMod,
    KeyChord,
    StandardKeyBinding,
)
from himena._descriptors import SaveToPath, NoNeedToSave
from himena.consts import MenuId, StandardType, IS_WINDOWS, IS_MACOS, IS_LINUX
from himena.utils.html import html_to_plain_text
from himena.widgets import MainWindow, SubWindow
from himena.types import (
    ClipboardDataModel,
    WindowState,
    WidgetDataModel,
)
from himena._app_model._context import AppContext as _ctx
from himena._app_model.actions._registry import ACTIONS, SUBMENUS
from himena import _utils, _providers
from himena.exceptions import Cancelled
from himena.workflow import LocalReaderMethod

_LOGGER = logging.getLogger(__name__)

EDIT_GROUP = "00_edit"
PROPERTY_GROUP = "01_property"
STATE_GROUP = "21_state"
MOVE_GROUP = "22_move"
ZOOM_GROUP = "40_zoom"
EXIT_GROUP = "99_exit"
_CtrlK = KeyMod.CtrlCmd | KeyCode.KeyK
_CtrlShift = KeyMod.CtrlCmd | KeyMod.Shift


@ACTIONS.append_from_fn(
    id="show-whats-this",
    title="What Is This Widget?",
    menus=[{"id": MenuId.WINDOW, "group": EXIT_GROUP}],
    enablement=_ctx.num_sub_windows > 0,
)
def show_whats_this(ui: MainWindow) -> None:
    """Show the docstring of the current widget."""
    if window := ui.current_window:
        if doc := getattr(window.widget, "__doc__", ""):
            doc_formatted = _utils.doc_to_whats_this(doc)
            ui._backend_main_window._add_whats_this(doc_formatted, style="markdown")


@ACTIONS.append_from_fn(
    id="show-workflow-graph",
    title="Show Workflow Graph",
    menus=[
        {"id": MenuId.WINDOW, "group": EXIT_GROUP},
        {"id": MenuId.TOOLBAR, "group": EXIT_GROUP},
    ],
    enablement=_ctx.num_sub_windows > 0,
    need_function_callback=True,
    icon="hugeicons:workflow-circle-05",
)
def show_workflow_graph(model: WidgetDataModel) -> WidgetDataModel:
    """Show the workflow graph of the current window."""
    workflow = model.workflow
    return WidgetDataModel(
        value=workflow.deep_copy(),
        type=StandardType.WORKFLOW,
        title=f"Workflow of {model.title}",
        save_behavior_override=NoNeedToSave(),
        extension_default=".workflow.json",
        workflow=workflow,
    )


@ACTIONS.append_from_fn(
    id="refresh-by-workflow",
    title="Refresh By Workflow",
    menus=[{"id": MenuId.WINDOW, "group": EXIT_GROUP}],
    enablement=_ctx.num_sub_windows > 0,
)
def refresh_by_workflow(win: SubWindow) -> None:
    """Refresh the current window by re-calculating its workflow."""
    model = win.to_model()
    model_out = model.workflow.compute(process_output=False)
    win.update_model(model_out)


@ACTIONS.append_from_fn(
    id="open-last-closed-window",
    title="Open Last Closed Window",
    menus=[{"id": MenuId.WINDOW, "group": EXIT_GROUP}],
    keybindings=[{"primary": _CtrlShift | KeyCode.KeyT}],
)
def open_last_closed_window(ui: MainWindow) -> WidgetDataModel:
    """Open the last closed window."""
    if last := ui._history_closed.pop_last():
        path, plugin = last
        store = _providers.ReaderStore().instance()
        model = store.run(path=path, plugin=plugin)
        model.workflow = LocalReaderMethod(
            output_model_type=model.type, plugin=plugin, path=path
        ).construct_workflow()
        return model
    warnings.warn("No window to reopen", UserWarning, stacklevel=2)
    raise Cancelled


@ACTIONS.append_from_fn(
    id="close-window",
    title="Close Window",
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
    id="duplicate-window",
    title="Duplicate Window",
    enablement=_ctx.is_active_window_supports_to_model,
    menus=[{"id": MenuId.WINDOW, "group": EDIT_GROUP}],
    keybindings=[{"primary": KeyChord(_CtrlK, _CtrlShift | KeyCode.KeyD)}],
    need_function_callback=True,
)
def duplicate_window(win: SubWindow) -> WidgetDataModel:
    """Duplicate the selected sub-window."""
    # NOTE: whether this copies the internal data depends on the widget.
    model = win.to_model()
    update = {
        "save_behavior_override": NoNeedToSave(),
        "force_open_with": _utils.get_widget_class_id(type(win.widget)),
    }
    if model.title is not None:
        model = model.with_title_numbering()
    if win.tab_area.is_single_window:
        model = model.use_tab()
    return model.model_copy(update=update)


@ACTIONS.append_from_fn(
    id="rename-window",
    title="Rename Window",
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
    if (i_win := ui._backend_main_window._current_sub_window_index(i_tab)) is not None:
        ui._backend_main_window._rename_window_at(i_tab, i_win)
    return None


@ACTIONS.append_from_fn(
    id="copy-path-to-clipboard",
    title="Copy Path To Clipboard",
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
            raise ValueError("Window does not have the source path.")
    else:
        RuntimeError("No window is focused.")


@ACTIONS.append_from_fn(
    id="copy-data-to-clipboard",
    title="Copy Data To Clipboard",
    menus=[
        {"id": MenuId.WINDOW, "group": EDIT_GROUP},
    ],
    enablement=(_ctx.num_sub_windows > 0) & _ctx.is_active_window_supports_to_model,
    keybindings=[{"primary": KeyChord(_CtrlK, KeyMod.CtrlCmd | KeyCode.KeyC)}],
)
def copy_data_to_clipboard(model: WidgetDataModel) -> ClipboardDataModel:
    """Copy the data of the current window to the clipboard."""

    if model.is_subtype_of(StandardType.TEXT):
        if model.is_subtype_of(StandardType.HTML):
            return ClipboardDataModel(
                text=html_to_plain_text(model.value), html=model.value
            )
        else:
            return ClipboardDataModel(text=model.value)
    elif model.is_subtype_of(StandardType.IMAGE):
        return ClipboardDataModel(image=model.value)
    raise ValueError(f"Cannot convert {model.type} to a clipboard data.")


@ACTIONS.append_from_fn(
    id="minimize-window",
    title="Minimize Window",
    menus=[{"id": MenuId.WINDOW_RESIZE, "group": STATE_GROUP}],
    keybindings=[{"primary": KeyChord(_CtrlK, KeyMod.CtrlCmd | KeyCode.DownArrow)}],
    enablement=(_ctx.num_sub_windows > 0) & (~_ctx.is_single_window_mode),
)
def minimize_current_window(win: SubWindow) -> None:
    """Minimize the window"""
    win.state = WindowState.MIN


@ACTIONS.append_from_fn(
    id="maximize-window",
    title="Maximize Window",
    menus=[{"id": MenuId.WINDOW_RESIZE, "group": STATE_GROUP}],
    enablement=(_ctx.num_sub_windows > 0) & (~_ctx.is_single_window_mode),
    keybindings=[{"primary": KeyChord(_CtrlK, KeyMod.CtrlCmd | KeyCode.UpArrow)}],
)
def maximize_current_window(win: SubWindow) -> None:
    win.state = WindowState.MAX


@ACTIONS.append_from_fn(
    id="toggle-full-screen",
    title="Toggle Full Screen",
    menus=[{"id": MenuId.WINDOW_RESIZE, "group": STATE_GROUP}],
    keybindings=[{"primary": KeyCode.F11}],
    enablement=(_ctx.num_sub_windows > 0) & (~_ctx.is_single_window_mode),
)
def toggle_full_screen(win: SubWindow) -> None:
    if win.state is WindowState.FULL:
        win.state = WindowState.NORMAL
    else:
        win.state = WindowState.FULL


@ACTIONS.append_from_fn(
    id="unset-anchor",
    title="Unanchor Window",
    menus=[MenuId.WINDOW_ANCHOR],
    enablement=_ctx.num_sub_windows > 0,
)
def unset_anchor(win: SubWindow) -> None:
    """Unset the anchor of the window if exists."""
    win.anchor = None


@ACTIONS.append_from_fn(
    id="anchor-window-top-left",
    title="Anchor Window To Top-Left Corner",
    menus=[MenuId.WINDOW_ANCHOR],
    enablement=_ctx.num_sub_windows > 0,
)
def anchor_at_top_left(win: SubWindow) -> None:
    """Anchor the window at the top-left corner of the current window position."""
    win.anchor = "top-left"


@ACTIONS.append_from_fn(
    id="anchor-window-top-right",
    title="Anchor Window To Top-Right Corner",
    menus=[MenuId.WINDOW_ANCHOR],
    enablement=_ctx.num_sub_windows > 0,
)
def anchor_at_top_right(win: SubWindow) -> None:
    """Anchor the window at the top-right corner of the current window position."""
    win.anchor = "top-right"


@ACTIONS.append_from_fn(
    id="anchor-window-bottom-left",
    title="Anchor Window To Bottom-Left Corner",
    menus=[MenuId.WINDOW_ANCHOR],
    enablement=_ctx.num_sub_windows > 0,
)
def anchor_at_bottom_left(win: SubWindow) -> None:
    """Anchor the window at the bottom-left corner of the current window position."""
    win.anchor = "bottom-left"


@ACTIONS.append_from_fn(
    id="anchor-window-bottom-right",
    title="Anchor Window To Bottom-Right Corner",
    menus=[MenuId.WINDOW_ANCHOR],
    enablement=_ctx.num_sub_windows > 0,
)
def anchor_at_bottom_right(win: SubWindow) -> None:
    """Anchor the window at the bottom-right corner of the current window position."""
    win.anchor = "bottom-right"


@ACTIONS.append_from_fn(
    id="window-expand",
    title="Expand (+20%)",
    enablement=(_ctx.num_sub_windows > 0) & (~_ctx.is_single_window_mode),
    menus=[{"id": MenuId.WINDOW_RESIZE, "group": ZOOM_GROUP}],
    keybindings=[StandardKeyBinding.ZoomIn],
)
def window_expand(win: SubWindow) -> None:
    """Expand (increase the size of) the current window."""
    if win.state is WindowState.NORMAL:
        win._set_rect(win.rect.resize_relative(1.2, 1.2))


@ACTIONS.append_from_fn(
    id="window-shrink",
    title="Shrink (-20%)",
    enablement=(_ctx.num_sub_windows > 0) & (~_ctx.is_single_window_mode),
    menus=[{"id": MenuId.WINDOW_RESIZE, "group": ZOOM_GROUP}],
    keybindings=[StandardKeyBinding.ZoomOut],
)
def window_shrink(win: SubWindow) -> None:
    """Shrink (reduce the size of) the current window."""
    if win.state is WindowState.NORMAL:
        win._set_rect(win.rect.resize_relative(1 / 1.2, 1 / 1.2))


@ACTIONS.append_from_fn(
    id="full-screen-in-new-tab",
    title="Full Screen In New Tab",
    enablement=(_ctx.num_sub_windows > 0) & (~_ctx.is_single_window_mode),
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


@ACTIONS.append_from_fn(
    id="reveal-in-explorer",
    title="Reveal In Explorer",
    enablement=_ctx.num_sub_windows > 0,
    menus=[{"id": MenuId.WINDOW, "group": EDIT_GROUP}],
)
def reveal_in_explorer(win: SubWindow):
    from subprocess import Popen

    if isinstance(win.save_behavior, SaveToPath) and win.save_behavior.path.exists():
        path = win.save_behavior.path
    elif isinstance(source := win.to_model().source, Path) and source.exists():
        path = source
    else:
        raise ValueError("Could not determine the source file of the window.")

    if IS_MACOS:
        if path.is_dir():
            Popen(["open", "-R", str(path)])
        else:
            Popen(["open", "-R", str(path.parent)])
    elif IS_WINDOWS:
        Popen(["explorer", "/select,", str(path)])
    elif IS_LINUX:
        Popen(["xdg-open", str(path.parent)])
    else:
        raise NotImplementedError(f"Platform {sys.platform} is not supported")


_CtrlAlt = KeyMod.CtrlCmd | KeyMod.Alt


@ACTIONS.append_from_fn(
    id="align-window-left",
    title="Align Window To Left",
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
    title="Align Window To Right",
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
    title="Align Window To Top",
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
    title="Align Window To Bottom",
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
    title="Align Window To Center",
    enablement=_ctx.num_sub_windows > 0,
    menus=[MenuId.WINDOW_ALIGN],
    keybindings=[{"primary": _CtrlAlt | KeyCode.Space}],
)
def align_window_center(ui: MainWindow) -> None:
    """Align the window to the center of the tab area."""
    if window := ui.current_window:
        window._set_rect(window.rect.align_center(ui.area_size))


def toggle_editable(win: SubWindow) -> None:
    win.is_editable = not win.is_editable


def toggle_track_modification(win: SubWindow) -> None:
    win._set_modification_tracking(not win._data_modifications.track_enabled)


ACTIONS.append(
    Action(
        id="window-toggle-editable",
        title="Window Editable",
        callback=toggle_editable,
        enablement=_ctx.is_subwindow_focused,
        menus=[{"id": MenuId.WINDOW, "group": PROPERTY_GROUP}],
        toggled=ToggleRule(condition=_ctx.is_active_window_editable),
    )
)

ACTIONS.append(
    Action(
        id="window-toggle-track-modifications",
        title="Track User Modifications",
        callback=toggle_editable,
        enablement=_ctx.is_subwindow_focused,
        menus=[{"id": MenuId.WINDOW, "group": PROPERTY_GROUP}],
        toggled=ToggleRule(condition=_ctx.is_active_window_track_modification),
    )
)


SUBMENUS.append_from(
    id=MenuId.WINDOW,
    submenu=MenuId.WINDOW_RESIZE,
    title="Resize",
    enablement=(_ctx.num_sub_windows > 0) & (~_ctx.is_single_window_mode),
    group=MOVE_GROUP,
)
SUBMENUS.append_from(
    id=MenuId.WINDOW,
    submenu=MenuId.WINDOW_ALIGN,
    title="Align",
    enablement=(_ctx.num_sub_windows > 0) & (~_ctx.is_single_window_mode),
    group=MOVE_GROUP,
)
SUBMENUS.append_from(
    id=MenuId.WINDOW,
    submenu=MenuId.WINDOW_ANCHOR,
    title="Anchor",
    enablement=(_ctx.num_sub_windows > 0) & (~_ctx.is_single_window_mode),
    group=MOVE_GROUP,
)
