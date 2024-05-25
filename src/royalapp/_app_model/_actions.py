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


def save_from_dialog(ui: MainWindowMixin) -> FileData:
    file_path = ui._open_file_dialog(mode="w")
    if file_path is None:
        return None
    writers = get_writers(file_path)
    return writers[0](file_path)


def exit_main_window(ui: MainWindowMixin) -> None:
    ui._close_window()


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
        id="close",
        title="Exit",
        icon="fa-solid:window-close",
        callback=exit_main_window,
        menus=["file"],
        keybindings=[KeyBindingRule(primary=KeyMod.CtrlCmd | KeyCode.KeyQ)],
    ),
]
