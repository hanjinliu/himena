from pathlib import Path
from typing import Any, Callable
from app_model.types import (
    KeyBindingRule,
    KeyCode,
    KeyMod,
    KeyChord,
    StandardKeyBinding,
)
from himena._descriptors import SaveBehavior
from himena.consts import StandardTypes, MenuId
from himena.widgets import MainWindow
from himena import io, _utils
from himena.types import (
    ClipboardDataModel,
    Parametric,
    WidgetDataModel,
    ReaderFunction,
)
from himena._app_model._context import AppContext as _ctx
from himena._app_model.actions._registry import ACTIONS, SUBMENUS

_CtrlK = KeyMod.CtrlCmd | KeyCode.KeyK

READ_GROUP = "00_io_read"
WRITE_GROUP = "01_io_write"
SCR_SHOT_GROUP = "21_screenshot"
COPY_SCR_SHOT = "00_copy-screenshot"
SAVE_SCR_SHOT = "01_save-screenshot"
EXIT_GROUP = "99_exit"


def _read_and_update_source(reader: io.ReaderTuple, source: Path) -> WidgetDataModel:
    """Update the `method` attribute if it is not set."""
    model = reader.read(source)
    if model.method is None:
        model = model._with_source(source=source, plugin=reader.plugin)
    return model


def _name_of(f: Callable) -> str:
    return getattr(f, "__name__", str(f))


@ACTIONS.append_from_fn(
    id="open-file",
    title="Open File(s) ...",
    icon="material-symbols:folder-open-outline",
    menus=[
        {"id": MenuId.FILE, "group": READ_GROUP},
        {"id": MenuId.TOOLBAR, "group": READ_GROUP},
    ],
    keybindings=[StandardKeyBinding.Open],
)
def open_file_from_dialog(ui: MainWindow) -> list[WidgetDataModel]:
    """Open file(s). Multiple files will be opened as separate sub-windows."""
    file_paths = ui.exec_file_dialog(mode="rm")
    if file_paths is None or len(file_paths) == 0:
        return None
    reader_path_sets: list[tuple[ReaderFunction, Any]] = []
    for file_path in file_paths:
        reader_path_sets.append((io.pick_reader(file_path), file_path))
    out = [
        _read_and_update_source(reader, file_path)
        for reader, file_path in reader_path_sets
    ]
    ui._recent_manager.append_recent_files(file_paths)
    return out


@ACTIONS.append_from_fn(
    id="open-file-using",
    title="Open File Using ...",
    menus=[{"id": MenuId.FILE, "group": READ_GROUP}],
    need_function_callback=True,
)
def open_file_using_from_dialog(ui: MainWindow) -> Parametric:
    """Open file using selected plugin."""
    from himena.plugins import configure_gui

    file_path = ui.exec_file_dialog(mode="r")
    if file_path is None:
        return None
    readers = io.get_readers(file_path)

    # prepare reader plugin choices
    choices_reader = [(f"{_name_of(r.reader)}\n({r.plugin.name})", r) for r in readers]

    @configure_gui(
        reader={
            "choices": choices_reader,
            "widget_type": "RadioButtons",
            "value": choices_reader[0][1],
        }
    )
    def choose_a_plugin(reader: io.ReaderTuple) -> Parametric:
        model = _read_and_update_source(reader, file_path)
        ui._recent_manager.append_recent_files([file_path])
        return ui._prep_choose_plugin_func(model)

    return _utils.make_function_callback(choose_a_plugin, command_id="open-file-with")


@ACTIONS.append_from_fn(
    id="open-folder",
    title="Open Folder ...",
    icon="material-symbols:folder-open",
    menus=[{"id": MenuId.FILE, "group": READ_GROUP}],
)
def open_folder_from_dialog(ui: MainWindow) -> WidgetDataModel:
    """Open a folder as a sub-window."""
    file_path = ui.exec_file_dialog(mode="d")
    if file_path is None:
        return None
    out = _read_and_update_source(io.pick_reader(file_path), file_path)
    ui._recent_manager.append_recent_files([file_path])
    return out


@ACTIONS.append_from_fn(
    id="save",
    title="Save ...",
    icon="material-symbols:save-outline",
    menus=[
        {"id": MenuId.FILE, "group": WRITE_GROUP},
        {"id": MenuId.TOOLBAR, "group": WRITE_GROUP},
    ],
    keybindings=[StandardKeyBinding.Save],
    enablement=_ctx.is_active_window_exportable,
)
def save_from_dialog(ui: MainWindow) -> None:
    """Save (overwrite) the current sub-window as a file."""
    fd, sub_win = ui._provide_file_output()
    if save_path := sub_win.save_behavior.get_save_path(ui, fd):
        io.write(fd, save_path)
        sub_win.update_default_save_path(save_path)
    return None


@ACTIONS.append_from_fn(
    id="save-as",
    title="Save As ...",
    icon="material-symbols:save-as-outline",
    menus=[{"id": MenuId.FILE, "group": WRITE_GROUP}],
    keybindings=[StandardKeyBinding.SaveAs],
    enablement=_ctx.is_active_window_exportable,
)
def save_as_from_dialog(ui: MainWindow) -> None:
    """Save the current sub-window as a new file."""
    fd, sub_win = ui._provide_file_output()
    if save_path := SaveBehavior().get_save_path(ui, fd):
        io.write(fd, save_path)
        sub_win.update_default_save_path(save_path)
    return None


@ACTIONS.append_from_fn(
    id="save-as-using",
    title="Save As Using ...",
    menus=[{"id": MenuId.FILE, "group": WRITE_GROUP}],
    need_function_callback=True,
    enablement=_ctx.is_active_window_exportable,
)
def save_as_using_from_dialog(ui: MainWindow, model: WidgetDataModel) -> Parametric:
    """Save the current sub-window using selected plugin."""
    from himena.plugins import configure_gui

    writers = io.get_writers(model)

    # prepare reader plugin choices
    choices_writer = [(f"{_name_of(w.writer)}\n({w.plugin.name})", w) for w in writers]

    @configure_gui(
        writer={
            "choices": choices_writer,
            "widget_type": "RadioButtons",
            "value": choices_writer[0][1],
        }
    )
    def choose_a_plugin(writer: io.WriterTuple) -> None:
        file_path = ui.exec_file_dialog(mode="w")
        if file_path is None:
            return None
        writer.write(model, file_path)
        return None

    return choose_a_plugin


@ACTIONS.append_from_fn(
    id="open-recent",
    title="Open Recent ...",
    icon="mdi:recent",
    menus=[{"id": MenuId.FILE_RECENT, "group": "02_more", "order": 99}],
    keybindings=[
        KeyBindingRule(primary=KeyChord(_CtrlK, KeyMod.CtrlCmd | KeyCode.KeyR))
    ],
)
def open_recent(ui: MainWindow) -> WidgetDataModel:
    """Open a recent file as a sub-window."""
    return ui._backend_main_window._show_command_palette("recent")


@ACTIONS.append_from_fn(
    id="paste-as-window",
    title="Paste as window",
    icon="material-symbols:content-paste",
    menus=[{"id": MenuId.FILE, "group": READ_GROUP}],
    keybindings=[StandardKeyBinding.Paste],
)
def paste_from_clipboard(ui: MainWindow) -> WidgetDataModel:
    """Paste the clipboard data as a sub-window."""
    if data := ui._backend_main_window._clipboard_data():
        return data.to_widget_data_model()
    return None


### Load/save session


@ACTIONS.append_from_fn(
    id="load-session",
    title="Load Session ...",
    menus=[{"id": MenuId.FILE, "group": READ_GROUP}],
    keybindings=[KeyBindingRule(primary=KeyMod.CtrlCmd | KeyCode.KeyL)],
)
def load_session_from_dialog(ui: MainWindow) -> None:
    """Load a session from a file."""
    if path := ui.exec_file_dialog(
        mode="r",
        allowed_extensions=[".session.yaml"],
    ):
        ui.read_session(path)
    return None


@ACTIONS.append_from_fn(
    id="save-session",
    title="Save Session ...",
    menus=[{"id": MenuId.FILE, "group": WRITE_GROUP}],
    enablement=_ctx.num_tabs > 0,
)
def save_session_from_dialog(ui: MainWindow) -> None:
    """Save current application state to a session."""
    if path := ui.exec_file_dialog(
        mode="w",
        extension_default=".session.yaml",
        allowed_extensions=[".session.yaml"],
    ):
        ui.save_session(path)
    return None


@ACTIONS.append_from_fn(
    id="save-tab-session",
    title="Save Tab Session ...",
    menus=[{"id": MenuId.FILE, "group": WRITE_GROUP}],
    enablement=(_ctx.num_tabs > 0) & (_ctx.num_sub_windows > 0),
)
def save_tab_session_from_dialog(ui: MainWindow) -> None:
    """Save current application state to a session."""
    if path := ui.exec_file_dialog(
        mode="w",
        extension_default=".session.yaml",
        allowed_extensions=[".session.yaml"],
    ):
        if tab := ui.tabs.current():
            tab.save_session(path)
    return None


@ACTIONS.append_from_fn(
    id="quit",
    title="Quit",
    menus=[{"id": MenuId.FILE, "group": EXIT_GROUP}],
    keybindings=[StandardKeyBinding.Quit],
)
def quit_main_window(ui: MainWindow) -> None:
    """Quit the application."""
    ui._backend_main_window._exit_main_window()


@ACTIONS.append_from_fn(
    id="copy-screenshot",
    title="Copy screenshot of entire main window",
    menus=[{"id": MenuId.FILE_SCREENSHOT, "group": COPY_SCR_SHOT}],
)
def copy_screenshot(ui: MainWindow) -> ClipboardDataModel:
    """Copy a screenshot of the main window to the clipboard."""
    data = ui._backend_main_window._screenshot("main")
    return ClipboardDataModel(value=data, type=StandardTypes.IMAGE)


@ACTIONS.append_from_fn(
    id="copy-screenshot-area",
    title="Copy screenshot of tab area",
    menus=[{"id": MenuId.FILE_SCREENSHOT, "group": COPY_SCR_SHOT}],
    enablement=_ctx.num_tabs > 0,
)
def copy_screenshot_area(ui: MainWindow) -> ClipboardDataModel:
    """Copy a screenshot of the tab area to the clipboard."""
    data = ui._backend_main_window._screenshot("area")
    return ClipboardDataModel(value=data, type=StandardTypes.IMAGE)


@ACTIONS.append_from_fn(
    id="copy-screenshot-window",
    title="Copy Screenshot of sub-window",
    menus=[{"id": MenuId.FILE_SCREENSHOT, "group": COPY_SCR_SHOT}],
    enablement=_ctx.num_sub_windows > 0,
)
def copy_screenshot_window(ui: MainWindow) -> ClipboardDataModel:
    """Copy a screenshot of the sub window to the clipboard."""
    data = ui._backend_main_window._screenshot("window")
    return ClipboardDataModel(value=data, type=StandardTypes.IMAGE)


def _save_screenshot(ui: MainWindow, target: str) -> None:
    from PIL import Image
    import numpy as np

    arr = ui._backend_main_window._screenshot(target)
    save_path = ui.exec_file_dialog(mode="w")
    if save_path is None:
        return
    img = Image.fromarray(np.asarray(arr))
    img.save(save_path)


@ACTIONS.append_from_fn(
    id="save-screenshot",
    title="Save screenshot of entire main window",
    menus=[{"id": MenuId.FILE_SCREENSHOT, "group": SAVE_SCR_SHOT}],
)
def save_screenshot(ui: MainWindow) -> None:
    _save_screenshot(ui, "main")


@ACTIONS.append_from_fn(
    id="save-screenshot-area",
    title="Save screenshot of tab area",
    menus=[{"id": MenuId.FILE_SCREENSHOT, "group": SAVE_SCR_SHOT}],
    enablement=_ctx.num_tabs > 0,
)
def save_screenshot_area(ui: MainWindow) -> None:
    _save_screenshot(ui, "area")


@ACTIONS.append_from_fn(
    id="save-screenshot-window",
    title="Save screenshot of sub-window",
    menus=[{"id": MenuId.FILE_SCREENSHOT, "group": SAVE_SCR_SHOT}],
    enablement=_ctx.num_sub_windows > 0,
)
def save_screenshot_window(ui: MainWindow) -> None:
    _save_screenshot(ui, "window")


SUBMENUS.append_from(
    id=MenuId.FILE,
    submenu=MenuId.FILE_RECENT,
    title="Open Recent",
    group=READ_GROUP,
)
SUBMENUS.append_from(
    id=MenuId.FILE,
    submenu=MenuId.FILE_NEW,
    title="New",
    group=READ_GROUP,
)
SUBMENUS.append_from(
    id=MenuId.FILE,
    submenu=MenuId.FILE_SCREENSHOT,
    title="Screenshot",
    group=SCR_SHOT_GROUP,
)
