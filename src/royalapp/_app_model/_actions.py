from app_model.types import Action, KeyBindingRule, KeyCode, KeyMod
from royalapp.widgets import MainWindow
from royalapp.io import get_readers, get_writers
from royalapp.types import WidgetDataModel, WindowTitle
from royalapp._app_model._context import MainWindowContexts


def open_from_dialog(ui: MainWindow) -> WidgetDataModel:
    file_path = ui._backend_main_window._open_file_dialog()
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


def close_current_tab(ui: MainWindow) -> None:
    idx = ui._backend_main_window._current_tab_index()
    if idx is not None:
        ui.tabs.pop(idx)


def close_current_window(ui: MainWindow) -> None:
    i_tab = ui._backend_main_window._current_tab_index()
    if i_tab is None:
        return None
    i_window = ui._backend_main_window._current_sub_window_index()
    if i_window is None:
        return None
    ui._backend_main_window._del_widget_at(i_tab, i_window)


def test_command(ui: MainWindow, title: WindowTitle) -> WidgetDataModel:
    return ui.tabs.current().current().widget.export_data()


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
        enablement=MainWindowContexts.is_active_window_savable,
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
        enablement=MainWindowContexts.is_active_window_savable,
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
    # Just for test
    Action(
        id="test",
        title="Test",
        callback=test_command,
        menus=["edit"],
    ),
]
