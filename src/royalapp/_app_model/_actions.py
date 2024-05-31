from app_model.types import Action, KeyBindingRule, KeyCode, KeyMod, KeyChord
from royalapp.widgets import MainWindow
from royalapp.io import get_readers, get_writers
from royalapp.types import WidgetDataModel
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
    if area := ui.tabs.current_or():
        area.clear()


def copy_window(model: WidgetDataModel) -> WidgetDataModel:
    if model.title is not None:
        model.title += " (copy)"
    return model


def new_tab(ui: MainWindow) -> None:
    ui.add_tab()


def close_current_tab(ui: MainWindow) -> None:
    idx = ui._backend_main_window._current_tab_index()
    if idx is not None:
        ui.tabs.pop(idx)


_CtrlK = KeyMod.CtrlCmd | KeyCode.KeyK

ACTIONS: list[Action] = [
    Action(
        id="open",
        title="Open",
        icon="material-symbols:folder-open-outline",
        callback=open_file_from_dialog,
        menus=["file", "toolbar"],
        keybindings=[KeyBindingRule(primary=KeyMod.CtrlCmd | KeyCode.KeyO)],
    ),
    Action(
        id="open-folder",
        title="Open Folder",
        icon="material-symbols:folder-open-outline",
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
        id="close-window",
        title="Close window",
        icon="material-symbols:tab-close-outline",
        callback=close_current_window,
        menus=["window"],
        keybindings=[KeyBindingRule(primary=KeyMod.CtrlCmd | KeyCode.KeyW)],
        enablement=~_ctx.is_active_tab_empty,
    ),
    Action(
        id="close-all-window",
        title="Close all windows in tab",
        callback=close_all_windows_in_tab,
        menus=["window"],
        enablement=~_ctx.is_active_tab_empty,
    ),
    Action(
        id="exit",
        title="Exit",
        callback=exit_main_window,
        menus=["file"],
        keybindings=[KeyBindingRule(primary=KeyMod.CtrlCmd | KeyCode.KeyQ)],
    ),
    Action(
        id="copy-window",
        title="Copy current window",
        callback=copy_window,
        menus=["window"],
        enablement=_ctx.is_active_window_exportable,
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
    ),
]
