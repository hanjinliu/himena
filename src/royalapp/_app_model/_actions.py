from app_model.types import Action, KeyBindingRule, KeyCode, KeyMod
from royalapp._app_model._app_registry import MainWindowMixin
from royalapp.io import get_readers, get_writers
from royalapp.types import FileData


def open_from_dialog(ui: MainWindowMixin) -> FileData:
    file_path = ui._open_file_dialog()
    if file_path is None:
        return None
    readers = get_readers(file_path)
    return readers[0](file_path)


def save_from_dialog(ui: MainWindowMixin) -> None:
    fd = ui._provide_file_output()
    if fd.file_path is None:
        save_path = ui._open_file_dialog(mode="w")
        if save_path is None:
            return
        fd.file_path = save_path
    else:
        ok = ui._open_confirmation_dialog("File exists, overwrite?")
        if not ok:
            return None

    writers = get_writers(fd)
    return writers[0](fd)


def save_as_from_dialog(ui: MainWindowMixin) -> None:
    fd = ui._provide_file_output()
    save_path = ui._open_file_dialog(mode="w")
    if save_path is None:
        return
    fd.file_path = save_path
    writers = get_writers(fd)
    return writers[0](fd)


def exit_main_window(ui: MainWindowMixin) -> None:
    ui._exit_main_window()


def close_current_window(ui: MainWindowMixin) -> None:
    ui._close_current_window()


ACTIONS: list[Action] = [
    Action(
        id="open",
        title="Open",
        icon="material-symbols:folder-open-outline",
        callback=open_from_dialog,
        menus=["file", "toolbar"],
        keybindings=[KeyBindingRule(primary=KeyMod.CtrlCmd | KeyCode.KeyO)],
    ),
    Action(
        id="save",
        title="Save",
        icon="material-symbols:save-outline",
        callback=save_from_dialog,
        menus=["file", "toolbar"],
        keybindings=[KeyBindingRule(primary=KeyMod.CtrlCmd | KeyCode.KeyS)],
    ),
    Action(
        id="save_as",
        title="Save As",
        icon="material-symbols:save-as-outline",
        callback=save_as_from_dialog,
        menus=["file"],
        keybindings=[
            KeyBindingRule(primary=KeyMod.CtrlCmd | KeyMod.Shift | KeyCode.KeyS)
        ],
    ),
    Action(
        id="close",
        title="Close",
        icon="material-symbols:tab-close-outline",
        callback=close_current_window,
        menus=["file"],
        keybindings=[KeyBindingRule(primary=KeyMod.CtrlCmd | KeyCode.KeyW)],
    ),
    Action(
        id="exit",
        title="Exit",
        callback=exit_main_window,
        menus=["file"],
        keybindings=[KeyBindingRule(primary=KeyMod.CtrlCmd | KeyCode.KeyQ)],
    ),
]
