from app_model.types import (
    Action,
    KeyBindingRule,
    KeyCode,
    KeyMod,
    KeyChord,
    SubmenuItem,
)
from royalapp.consts import StandardTypes
from royalapp.widgets import MainWindow
from royalapp.io import get_readers, get_writers
from royalapp.types import ClipboardDataModel, SubWindowState, WidgetDataModel
from royalapp._app_model._context import AppContext as _ctx


def open_file_from_dialog(ui: MainWindow) -> WidgetDataModel:
    file_path = ui._backend_main_window._open_file_dialog()
    if file_path is None:
        return None
    readers = get_readers(file_path)
    return readers[0](file_path)


def open_folder_from_dialog(ui: MainWindow) -> WidgetDataModel:
    file_path = ui._backend_main_window._open_file_dialog("d")
    if file_path is None:
        return None
    readers = get_readers(file_path)
    return readers[0](file_path)


def save_from_dialog(ui: MainWindow) -> None:
    fd = ui._backend_main_window._provide_file_output()
    if fd.source is None:
        save_path = ui._backend_main_window._open_file_dialog(mode="w")
        if save_path is None:
            return
        fd.source = save_path
    else:
        if fd.source.exists():
            _path = fd.source.as_posix()
            ok = ui._backend_main_window._open_confirmation_dialog(
                f"{_path!r} already exists, overwrite?"
            )
            if not ok:
                return None

    writers = get_writers(fd)
    return writers[0](fd)


def paste_from_clipboard(ui: MainWindow) -> WidgetDataModel:
    if data := ui._backend_main_window._clipboard_data():
        return data.to_widget_data_model()
    return None


def save_as_from_dialog(ui: MainWindow) -> None:
    fd = ui._backend_main_window._provide_file_output()
    save_path = ui._backend_main_window._open_file_dialog(mode="w")
    if save_path is None:
        return
    fd.source = save_path
    writers = get_writers(fd)
    return writers[0](fd)


def exit_main_window(ui: MainWindow) -> None:
    ui._backend_main_window._exit_main_window()


def close_current_window(ui: MainWindow) -> None:
    i_tab = ui.tabs.current_index()
    if i_tab is None:
        return None
    i_window = ui.tabs.current_index()
    if i_window is None:
        return None
    del ui.tabs[i_tab][i_window]


def close_all_windows_in_tab(ui: MainWindow) -> None:
    if area := ui.tabs.current():
        area.clear()


def copy_window(model: WidgetDataModel) -> WidgetDataModel:
    if model.title is not None:
        model.title += " (copy)"
    return model


def minimize_others(ui: MainWindow):
    if area := ui.tabs.current():
        cur_window = area.current()
        for window in area:
            if cur_window is window:
                continue
            window.state = SubWindowState.MIN


def show_all_windows(ui: MainWindow):
    if area := ui.tabs.current():
        for window in area:
            if window.state is SubWindowState.MIN:
                window.state = SubWindowState.NORMAL


def new_tab(ui: MainWindow) -> None:
    ui.add_tab()


def close_current_tab(ui: MainWindow) -> None:
    idx = ui._backend_main_window._current_tab_index()
    if idx is not None:
        ui.tabs.pop(idx)


def copy_screenshot(ui: MainWindow) -> ClipboardDataModel:
    data = ui._backend_main_window._screenshot("main")
    return ClipboardDataModel(value=data, type=StandardTypes.IMAGE)


def copy_screenshot_area(ui: MainWindow) -> ClipboardDataModel:
    data = ui._backend_main_window._screenshot("area")
    return ClipboardDataModel(value=data, type=StandardTypes.IMAGE)


def copy_screenshot_window(ui: MainWindow) -> ClipboardDataModel:
    data = ui._backend_main_window._screenshot("window")
    return ClipboardDataModel(value=data, type=StandardTypes.IMAGE)


def _save_screenshot(ui: MainWindow, target: str) -> None:
    from PIL import Image
    import numpy as np

    arr = ui._backend_main_window._screenshot(target)
    save_path = ui._backend_main_window._open_file_dialog(mode="w")
    if save_path is None:
        return
    img = Image.fromarray(np.asarray(arr))
    img.save(save_path)


def save_screenshot(ui: MainWindow) -> None:
    _save_screenshot(ui, "main")


def save_screenshot_area(ui: MainWindow) -> None:
    _save_screenshot(ui, "area")


def save_screenshot_window(ui: MainWindow) -> None:
    _save_screenshot(ui, "window")


def tile_windows(ui: MainWindow) -> None:
    if area := ui.tabs.current():
        area.tile_windows()


_CtrlK = KeyMod.CtrlCmd | KeyCode.KeyK

ACTIONS_AND_MENUS = [
    Action(
        id="open",
        title="Open File(s)",
        icon="material-symbols:folder-open-outline",
        callback=open_file_from_dialog,
        menus=["file", "toolbar"],
        keybindings=[KeyBindingRule(primary=KeyMod.CtrlCmd | KeyCode.KeyO)],
    ),
    Action(
        id="open-folder",
        title="Open Folder",
        icon="material-symbols:folder-open",
        callback=open_folder_from_dialog,
        menus=["file"],
        keybindings=[
            KeyBindingRule(primary=KeyChord(_CtrlK, KeyMod.CtrlCmd | KeyCode.KeyO))
        ],
    ),
    Action(
        id="save",
        title="Save",
        icon="material-symbols:save-outline",
        callback=save_from_dialog,
        menus=["file", "toolbar"],
        keybindings=[KeyBindingRule(primary=KeyMod.CtrlCmd | KeyCode.KeyS)],
        enablement=_ctx.is_active_window_exportable,
    ),
    Action(
        id="save-as",
        title="Save As",
        icon="material-symbols:save-as-outline",
        callback=save_as_from_dialog,
        menus=["file"],
        keybindings=[
            KeyBindingRule(primary=KeyMod.CtrlCmd | KeyMod.Shift | KeyCode.KeyS)
        ],
        enablement=_ctx.is_active_window_exportable,
    ),
    Action(
        id="paste",
        title="Paste as window",
        icon="material-symbols:content-paste",
        callback=paste_from_clipboard,
        menus=["file"],
    ),
    Action(
        id="close-window",
        title="Close window",
        icon="material-symbols:tab-close-outline",
        callback=close_current_window,
        menus=["window"],
        keybindings=[KeyBindingRule(primary=KeyMod.CtrlCmd | KeyCode.KeyW)],
        enablement=_ctx.has_sub_windows,
    ),
    Action(
        id="close-all-window",
        title="Close all windows in tab",
        callback=close_all_windows_in_tab,
        menus=["window"],
        enablement=_ctx.has_sub_windows,
    ),
    Action(
        id="copy-window",
        title="Copy current window",
        callback=copy_window,
        menus=["window"],
        enablement=_ctx.is_active_window_exportable,
    ),
    Action(
        id="minimize-other-windows",
        title="Minimize other windows",
        callback=minimize_others,
        menus=["window"],
        enablement=_ctx.has_sub_windows,
    ),
    Action(
        id="show-all-windows",
        title="Show all windows",
        callback=show_all_windows,
        menus=["window"],
        enablement=_ctx.has_sub_windows,
    ),
    Action(
        id="tile-windows",
        title="Tile windows",
        callback=tile_windows,
        menus=["window"],
        enablement=_ctx.has_sub_windows,
    ),
    Action(
        id="new-tab",
        title="New Tab",
        callback=new_tab,
        menus=["tab"],
        keybindings=[KeyBindingRule(primary=KeyMod.CtrlCmd | KeyCode.KeyT)],
    ),
    Action(
        id="close-tab",
        title="Close Tab",
        callback=close_current_tab,
        menus=["tab"],
        enablement=_ctx.has_tabs,
    ),
    [
        ("file", SubmenuItem(submenu="file/screenshot", title="Screenshot")),
        Action(
            id="copy-screenshot",
            title="Copy screenshot of entire main window",
            callback=copy_screenshot,
            menus=["file/screenshot"],
        ),
        Action(
            id="copy-screenshot-area",
            title="Copy screenshot of tab area",
            callback=copy_screenshot_area,
            menus=["file/screenshot"],
            enablement=_ctx.has_tabs,
        ),
        Action(
            id="copy-screenshot-window",
            title="Copy Screenshot of sub-window",
            callback=copy_screenshot_window,
            menus=["file/screenshot"],
            enablement=_ctx.has_sub_windows,
        ),
        Action(
            id="save-screenshot",
            title="Save screenshot of entire main window",
            callback=save_screenshot,
            menus=["file/screenshot"],
        ),
        Action(
            id="save-screenshot-area",
            title="Save screenshot of tab area",
            callback=save_screenshot_area,
            menus=["file/screenshot"],
            enablement=_ctx.has_tabs,
        ),
        Action(
            id="save-screenshot-window",
            title="Save screenshot of sub-window",
            callback=save_screenshot_window,
            menus=["file/screenshot"],
            enablement=_ctx.has_sub_windows,
        ),
    ],
    Action(
        id="exit",
        title="Exit",
        callback=exit_main_window,
        menus=["file"],
        keybindings=[KeyBindingRule(primary=KeyMod.CtrlCmd | KeyCode.KeyQ)],
    ),
]
