from pathlib import Path
from typing import Any
from app_model.types import (
    Action,
    KeyBindingRule,
    KeyCode,
    KeyMod,
    KeyChord,
    SubmenuItem,
)
from royalapp.consts import StandardTypes, MenuId
from royalapp.profile import append_recent_files
from royalapp.widgets import MainWindow
from royalapp.io import get_readers, get_writers
from royalapp.types import (
    ClipboardDataModel,
    WidgetDataModel,
    ReaderFunction,
)
from royalapp._app_model._context import AppContext as _ctx


def _read_and_update_source(reader: ReaderFunction, source: Path) -> WidgetDataModel:
    """Update the `method` attribute if it is not set."""
    model = reader(source)
    if model.method is None:
        model = model.with_source(source)
    return model


def open_file_from_dialog(ui: MainWindow) -> list[WidgetDataModel]:
    """Open files as separate sub-windows."""
    file_paths = ui._backend_main_window._open_file_dialog(mode="rm")
    if file_paths is None or len(file_paths) == 0:
        return None
    reader_path_sets: list[tuple[ReaderFunction, Any]] = []
    for file_path in file_paths:
        readers_matched = get_readers(file_path)
        reader_path_sets.append((readers_matched[0], file_path))
    out = [
        _read_and_update_source(reader, file_path)
        for reader, file_path in reader_path_sets
    ]
    append_recent_files(file_paths)
    ui._update_open_recent_menu()
    return out


def open_folder_from_dialog(ui: MainWindow) -> WidgetDataModel:
    """Open a folder as a sub-window."""
    file_path = ui._backend_main_window._open_file_dialog(mode="d")
    if file_path is None:
        return None
    readers = get_readers(file_path)
    out = _read_and_update_source(readers[0], file_path)
    append_recent_files([file_path])
    ui._update_open_recent_menu()
    return out


def save_from_dialog(ui: MainWindow) -> None:
    """Save (overwrite) the current sub-window as a file."""
    fd, sub_win = ui._provide_file_output()
    if save_path := sub_win.save_behavior.get_save_path(ui):
        writers = get_writers(fd)
        writers[0](fd, save_path)  # run save function
        sub_win.update_default_save_path(save_path)
    return None


def open_recent(ui: MainWindow) -> WidgetDataModel:
    """Open a recent file as a sub-window."""
    return ui._backend_main_window._show_command_palette("recent")


def paste_from_clipboard(ui: MainWindow) -> WidgetDataModel:
    """Paste the clipboard data as a sub-window."""
    if data := ui._backend_main_window._clipboard_data():
        return data.to_widget_data_model()
    return None


def save_as_from_dialog(ui: MainWindow) -> None:
    """Save the current sub-window as a new file."""
    fd, sub_win = ui._provide_file_output()
    if save_path := sub_win.save_behavior.get_save_path(ui):
        writers = get_writers(fd)
        writers[0](fd, save_path)
        sub_win.update_default_save_path(save_path)
    return None


def exit_main_window(ui: MainWindow) -> None:
    """Exit the application."""
    ui._backend_main_window._exit_main_window()


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


_CtrlK = KeyMod.CtrlCmd | KeyCode.KeyK

READ_GROUP = "00_io_read"
WRITE_GROUP = "01_io_write"
SCR_SHOT_GROUP = "21_screenshot"
COPY_SCR_SHOT = "00_copy-screenshot"
SAVE_SCR_SHOT = "01_save-screenshot"
EXIT_GROUP = "99_exit"

ACTIONS = [
    Action(
        id="open",
        title="Open File(s)",
        icon="material-symbols:folder-open-outline",
        callback=open_file_from_dialog,
        menus=[
            {"id": MenuId.FILE, "group": READ_GROUP},
            {"id": MenuId.TOOLBAR, "group": READ_GROUP},
        ],
        keybindings=[KeyBindingRule(primary=KeyMod.CtrlCmd | KeyCode.KeyO)],
        icon_visible_in_menu=False,
    ),
    Action(
        id="open-folder",
        title="Open Folder",
        icon="material-symbols:folder-open",
        callback=open_folder_from_dialog,
        menus=[{"id": MenuId.FILE, "group": READ_GROUP}],
        keybindings=[
            KeyBindingRule(primary=KeyChord(_CtrlK, KeyMod.CtrlCmd | KeyCode.KeyO))
        ],
        icon_visible_in_menu=False,
    ),
    Action(
        id="open-recent",
        title="Open Recent",
        icon="mdi:recent",
        callback=open_recent,
        menus=[
            {"id": MenuId.FILE_RECENT, "group": READ_GROUP, "order": 99},
            {"id": MenuId.TOOLBAR, "group": READ_GROUP, "order": 99},
        ],
        keybindings=[
            KeyBindingRule(primary=KeyChord(_CtrlK, KeyMod.CtrlCmd | KeyCode.KeyR))
        ],
        icon_visible_in_menu=False,
    ),
    Action(
        id="save",
        title="Save",
        icon="material-symbols:save-outline",
        callback=save_from_dialog,
        menus=[
            {"id": MenuId.FILE, "group": WRITE_GROUP},
            {"id": MenuId.TOOLBAR, "group": WRITE_GROUP},
        ],
        keybindings=[KeyBindingRule(primary=KeyMod.CtrlCmd | KeyCode.KeyS)],
        enablement=_ctx.is_active_window_exportable,
        icon_visible_in_menu=False,
    ),
    Action(
        id="save-as",
        title="Save As",
        icon="material-symbols:save-as-outline",
        callback=save_as_from_dialog,
        menus=[{"id": MenuId.FILE, "group": WRITE_GROUP}],
        keybindings=[
            KeyBindingRule(primary=KeyMod.CtrlCmd | KeyMod.Shift | KeyCode.KeyS)
        ],
        enablement=_ctx.is_active_window_exportable,
        icon_visible_in_menu=False,
    ),
    Action(
        id="paste",
        title="Paste as window",
        icon="material-symbols:content-paste",
        callback=paste_from_clipboard,
        menus=[{"id": MenuId.FILE, "group": READ_GROUP}],
        icon_visible_in_menu=False,
    ),
    Action(
        id="copy-screenshot",
        title="Copy screenshot of entire main window",
        callback=copy_screenshot,
        menus=[{"id": MenuId.FILE_SCREENSHOT, "group": COPY_SCR_SHOT}],
        icon_visible_in_menu=False,
    ),
    Action(
        id="copy-screenshot-area",
        title="Copy screenshot of tab area",
        callback=copy_screenshot_area,
        menus=[{"id": MenuId.FILE_SCREENSHOT, "group": COPY_SCR_SHOT}],
        enablement=_ctx.has_tabs,
        icon_visible_in_menu=False,
    ),
    Action(
        id="copy-screenshot-window",
        title="Copy Screenshot of sub-window",
        callback=copy_screenshot_window,
        menus=[{"id": MenuId.FILE_SCREENSHOT, "group": COPY_SCR_SHOT}],
        enablement=_ctx.has_sub_windows,
        icon_visible_in_menu=False,
    ),
    Action(
        id="save-screenshot",
        title="Save screenshot of entire main window",
        callback=save_screenshot,
        menus=[{"id": MenuId.FILE_SCREENSHOT, "group": SAVE_SCR_SHOT}],
        icon_visible_in_menu=False,
    ),
    Action(
        id="save-screenshot-area",
        title="Save screenshot of tab area",
        callback=save_screenshot_area,
        menus=[{"id": MenuId.FILE_SCREENSHOT, "group": SAVE_SCR_SHOT}],
        enablement=_ctx.has_tabs,
        icon_visible_in_menu=False,
    ),
    Action(
        id="save-screenshot-window",
        title="Save screenshot of sub-window",
        callback=save_screenshot_window,
        menus=[{"id": MenuId.FILE_SCREENSHOT, "group": SAVE_SCR_SHOT}],
        enablement=_ctx.has_sub_windows,
        icon_visible_in_menu=False,
    ),
    Action(
        id="exit",
        title="Exit",
        callback=exit_main_window,
        menus=[{"id": MenuId.FILE, "group": EXIT_GROUP}],
        keybindings=[KeyBindingRule(primary=KeyMod.CtrlCmd | KeyCode.KeyQ)],
        icon_visible_in_menu=False,
    ),
]

SUBMENUS = [
    (
        MenuId.FILE,
        SubmenuItem(
            submenu=MenuId.FILE_RECENT,
            title="Open Recent",
            group=READ_GROUP,
        ),
    ),
    (
        MenuId.FILE,
        SubmenuItem(
            submenu=MenuId.FILE_NEW,
            title="New",
            group=READ_GROUP,
        ),
    ),
    (
        MenuId.FILE,
        SubmenuItem(
            submenu=MenuId.FILE_SCREENSHOT,
            title="Screenshot",
            group=SCR_SHOT_GROUP,
        ),
    ),
]