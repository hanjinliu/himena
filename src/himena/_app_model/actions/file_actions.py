from concurrent.futures import Future
import datetime
from pathlib import Path
from typing import Callable
from logging import getLogger
from app_model.types import (
    KeyBindingRule,
    KeyCode,
    KeyMod,
    KeyChord,
    StandardKeyBinding,
)
from himena._data_wrappers import wrap_array
from himena._descriptors import SaveToNewPath, SaveToPath
from himena.consts import StandardType, MenuId
from himena.standards.model_meta import ImageMeta
from himena.widgets import MainWindow, SubWindow
from himena import _providers, workflow as _wf
from himena.types import (
    ClipboardDataModel,
    Parametric,
    WidgetDataModel,
)
from himena._app_model._context import AppContext as _ctx
from himena._app_model.actions._registry import ACTIONS, SUBMENUS
from himena.exceptions import Cancelled

_CtrlK = KeyMod.CtrlCmd | KeyCode.KeyK
_LOGGER = getLogger(__name__)

READ_GROUP = "00_io_read"
WRITE_GROUP = "01_io_write"
SCR_SHOT_GROUP = "21_screenshot"
SETTINGS_GROUP = "31_settings"
COPY_SCR_SHOT = "00_copy-screenshot"
SAVE_SCR_SHOT = "01_save-screenshot"
EXIT_GROUP = "99_exit"


def _name_of(f: Callable) -> str:
    return getattr(f, "__name__", str(f))


@ACTIONS.append_from_fn(
    id="open-file",
    title="Open File(s) ...",
    icon="material-symbols:folder-open-outline",
    menus=[
        {"id": MenuId.FILE, "group": READ_GROUP},
        {"id": MenuId.TOOLBAR, "group": READ_GROUP},
        {"id": MenuId.STARTUP, "group": READ_GROUP},
    ],
    keybindings=[StandardKeyBinding.Open],
)
def open_file_from_dialog(ui: MainWindow) -> Future:
    """Open file(s). Multiple files will be opened as separate sub-windows."""
    if result := ui.exec_file_dialog(mode="rm"):
        return ui.read_files_async(result)
    raise Cancelled


def _get_reader_options(file_path: Path) -> dict:
    _store = _providers.ReaderProviderStore.instance()
    readers = _store.get(file_path, min_priority=-float("inf"))

    # prepare reader plugin choices
    choices_reader = sorted(
        [(f"{_name_of(r.reader)}\n({r.plugin.name})", r) for r in readers],
        key=lambda x: x[1].priority,
        reverse=True,
    )
    return {
        "choices": choices_reader,
        "widget_type": "RadioButtons",
        "value": choices_reader[0][1],
    }


def _open_file_using_reader(
    file_path,
    reader: _providers.ReaderTuple,
    ui: MainWindow | None = None,
) -> WidgetDataModel:
    model = _providers.read_and_update_source(reader, file_path)
    if reader.plugin is not None:
        plugin = reader.plugin.to_str()
    else:
        plugin = None
    if ui:
        ui._recent_manager.append_recent_files([(file_path, plugin)])
    wf = _wf.LocalReaderMethod(
        path=file_path,
        plugin=plugin,
        output_model_type=model.type,
    ).construct_workflow()
    model.workflow = wf
    return model


@ACTIONS.append_from_fn(
    id="open-file-using",
    title="Open File Using ...",
    menus=[
        {"id": MenuId.FILE, "group": READ_GROUP},
        {"id": MenuId.STARTUP, "group": READ_GROUP},
    ],
    keybindings=[KeyBindingRule(primary=KeyMod.CtrlCmd | KeyMod.Shift | KeyCode.KeyO)],
    need_function_callback=True,
)
def open_file_using_from_dialog(ui: MainWindow) -> Parametric:
    """Open file using selected plugin."""
    from himena.plugins import configure_gui

    if (file_path := ui.exec_file_dialog(mode="r")) is None:
        raise Cancelled

    @configure_gui(reader=_get_reader_options(file_path), run_async=True)
    def choose_a_plugin(reader: _providers.ReaderTuple) -> WidgetDataModel:
        _LOGGER.info("Reading file %s using %r", file_path, reader)
        return _open_file_using_reader(file_path, reader, ui)

    return choose_a_plugin


@ACTIONS.append_from_fn(
    id="open-file-group",
    title="Open File Group ...",
    menus=[{"id": MenuId.FILE, "group": READ_GROUP}],
)
def open_file_group_from_dialog(ui: MainWindow) -> Future:
    """Open file group as a single sub-window."""
    if result := ui.exec_file_dialog(mode="rm"):
        return ui.read_files_async(result)
    raise Cancelled


@ACTIONS.append_from_fn(
    id="open-folder",
    title="Open Folder ...",
    icon="material-symbols:folder-open",
    menus=[
        {"id": MenuId.FILE, "group": READ_GROUP},
        {"id": MenuId.STARTUP, "group": READ_GROUP},
    ],
    keybindings=[
        KeyBindingRule(primary=KeyChord(_CtrlK, KeyMod.CtrlCmd | KeyCode.KeyO))
    ],
)
def open_folder_from_dialog(ui: MainWindow) -> Future:
    """Open a folder as a sub-window."""
    if path := ui.exec_file_dialog(mode="d"):
        return ui.read_files_async([path])
    raise Cancelled


@ACTIONS.append_from_fn(
    id="watch-file-using",
    title="Watch File ...",
    menus=[{"id": MenuId.FILE, "group": READ_GROUP}],
    need_function_callback=True,
)
def watch_file_using_from_dialog(ui: MainWindow) -> Parametric:
    """Watch file using selected plugin."""
    from himena.plugins import configure_gui

    if (file_path := ui.exec_file_dialog(mode="r")) is None:
        raise Cancelled

    @configure_gui(reader=_get_reader_options(file_path))
    def choose_a_plugin(reader: _providers.ReaderTuple) -> None:
        _LOGGER.info("Watch file %s using %r", file_path, reader)
        model = _open_file_using_reader(file_path, reader)
        win = ui.add_data_model(model)
        win._switch_to_file_watch_mode()
        return None

    return choose_a_plugin


@ACTIONS.append_from_fn(
    id="save",
    title="Save ...",
    icon="material-symbols:save-outline",
    menus=[
        {"id": MenuId.FILE, "group": WRITE_GROUP},
        {"id": MenuId.TOOLBAR, "group": WRITE_GROUP},
    ],
    keybindings=[StandardKeyBinding.Save],
    enablement=_ctx.is_active_window_supports_to_model,
)
def save_from_dialog(ui: MainWindow, sub_win: SubWindow) -> Future:
    """Save (overwrite) the current sub-window as a file."""
    if cb := sub_win._save_from_dialog(ui):
        return ui._executor.submit(cb)
    raise Cancelled


@ACTIONS.append_from_fn(
    id="save-as",
    title="Save As ...",
    icon="material-symbols:save-as-outline",
    menus=[{"id": MenuId.FILE, "group": WRITE_GROUP}],
    keybindings=[StandardKeyBinding.SaveAs],
    enablement=_ctx.is_active_window_supports_to_model,
)
def save_as_from_dialog(ui: MainWindow, sub_win: SubWindow) -> Future:
    """Save the current sub-window as a new file."""
    if cb := sub_win._save_from_dialog(ui, behavior=SaveToNewPath()):
        return ui._executor.submit(cb)
    raise Cancelled


@ACTIONS.append_from_fn(
    id="save-as-using",
    title="Save As Using ...",
    menus=[{"id": MenuId.FILE, "group": WRITE_GROUP}],
    need_function_callback=True,
    enablement=_ctx.is_active_window_supports_to_model,
)
def save_as_using_from_dialog(ui: MainWindow, sub_win: SubWindow) -> Future:
    """Save the current sub-window using selected plugin."""
    model = sub_win.to_model()
    ins = _providers.WriterProviderStore().instance()
    model.title = sub_win.title
    save_path = sub_win._save_behavior._determine_save_path(model) or "~"
    writers = ins.get(model, Path(save_path), min_priority=-float("inf"))

    # prepare reader plugin choices
    choices_writer = [(f"{_name_of(w.writer)}\n({w.plugin.name})", w) for w in writers]

    writer = ui.exec_choose_one_dialog(
        title="Choose a plugin",
        message="Choose a plugin to save the file.",
        choices=choices_writer,
        how="radiobuttons",
    )
    if writer is None:
        raise Cancelled  # no choice selected
    if cb := sub_win._save_from_dialog(
        ui, behavior=SaveToNewPath(), plugin=writer.plugin
    ):
        return ui._executor.submit(cb)
    else:
        raise Cancelled


@ACTIONS.append_from_fn(
    id="open-recent",
    title="Open Recent ...",
    menus=[{"id": MenuId.FILE_RECENT, "group": "02_more", "order": 99}],
    keybindings=[
        KeyBindingRule(primary=KeyChord(_CtrlK, KeyMod.CtrlCmd | KeyCode.KeyR))
    ],
    recording=False,
)
def open_recent(ui: MainWindow) -> WidgetDataModel:
    """Open a recent file as a sub-window."""
    return ui._backend_main_window._show_command_palette("recent")


@ACTIONS.append_from_fn(
    id="new",
    title="New ...",
    menus=[
        {"id": MenuId.FILE_NEW, "group": "02_more", "order": 99},
        {"id": MenuId.STARTUP, "group": READ_GROUP},
    ],
    keybindings=[StandardKeyBinding.New],
    recording=False,
)
def open_new(ui: MainWindow) -> WidgetDataModel:
    """Open a new file as a sub-window."""
    return ui._backend_main_window._show_command_palette("new")


@ACTIONS.append_from_fn(
    id="paste-as-window",
    title="Paste as window",
    menus=[MenuId.FILE_NEW],
    enablement=~_ctx.is_subwindow_focused,
    keybindings=[StandardKeyBinding.Paste],
)
def paste_from_clipboard(ui: MainWindow) -> WidgetDataModel:
    """Paste the clipboard data as a sub-window."""
    if data := ui._backend_main_window._clipboard_data():
        title = "Clipboard"
        if (image := data.image) is not None:
            shape = wrap_array(image).shape
            if len(shape) == 3 and shape[-1] in (3, 4):
                meta = ImageMeta(axes=["y", "x", "c"], is_rgb=True)
            else:
                meta = None
            return WidgetDataModel(
                value=image, type=StandardType.IMAGE, title=title, metadata=meta
            )
        elif files := data.files:
            ui.read_files(files)
            return None
        elif html := data.html:
            return WidgetDataModel(value=html, type=StandardType.HTML, title=title)
        elif text := data.text:
            return WidgetDataModel(value=text, type=StandardType.TEXT, title=title)
        raise ValueError("No data to paste from clipboard.")
    raise Cancelled


### Load/save session


@ACTIONS.append_from_fn(
    id="load-session",
    title="Load Session ...",
    menus=[
        {"id": MenuId.FILE_SESSION, "group": READ_GROUP},
        {"id": MenuId.STARTUP, "group": READ_GROUP},
    ],
    keybindings=[KeyBindingRule(primary=KeyMod.CtrlCmd | KeyCode.KeyL)],
)
def load_session_from_dialog(ui: MainWindow) -> None:
    """Load a application session from a file."""
    if path := ui.exec_file_dialog(
        mode="r",
        allowed_extensions=[".session.yaml", ".session.yml", ".session.zip"],
        group="session",
    ):
        ui.load_session(path)
    raise Cancelled


@ACTIONS.append_from_fn(
    id="save-session",
    title="Save Session ...",
    menus=[{"id": MenuId.FILE_SESSION, "group": WRITE_GROUP}],
    enablement=_ctx.num_tabs > 0,
)
def save_session_from_dialog(ui: MainWindow) -> None:
    """Save current application state to a session."""
    need_save: list[SubWindow] = []
    need_overwrite: list[SubWindow] = []
    for win in ui.iter_windows():
        if win._determine_read_from() is None:
            need_save.append(win)
        elif win._need_ask_save_before_close():
            if isinstance(win.save_behavior, SaveToPath):
                need_overwrite.append(win)
            else:
                need_save.append(win)
    # NOTE: need_save and need_overwrite are disjoint.
    allow_calc = False
    if need_save:
        _CS = "Save one by one"
        _CJ = "Just skip"
        _CR = "Recalculate when loaded"
        _CC = "Cancel"
        _list = "".join([f"<li>{win.title}</li>" for win in need_save])
        res = ui.exec_choose_one_dialog(
            title="Not saved windows",
            message=(
                f"Following windows are not saved yet.<ul>{_list}</ul>"
                "Do you want to save them?"
            ),
            choices=[_CS, _CJ, _CR, _CC],
            how="radiobuttons",
        )
        if res == _CS:
            for win in need_save:
                ui.current_window = win
                if cb := win._save_from_dialog(ui, behavior=SaveToNewPath()):
                    cb()
                else:
                    raise Cancelled
        elif res == _CJ:
            pass
        elif res == _CR:
            allow_calc = True
        else:
            raise Cancelled
    if need_overwrite:
        _CO = "Overwrite all"
        _CK = "Keep original"
        _CC = "Cancel"
        _list = "".join([f"<li>{win.title}</li>" for win in need_overwrite])
        res = ui.exec_choose_one_dialog(
            title="Modified windows",
            message=(
                f"Following window are modified.<ul>{_list}</ul>"
                "Do you want to overwrite them?"
            ),
            choices=[_CO, _CK, _CC],
        )
        if res == _CO:
            for win in need_overwrite:
                assert isinstance(win.save_behavior, SaveToPath)
                win.write_model(win.save_behavior.path, win.save_behavior.plugin)
        elif res == _CK:
            pass
        else:
            raise Cancelled
    datetime_str = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    if path := ui.exec_file_dialog(
        mode="w",
        extension_default=".session.yaml",
        allowed_extensions=[".session.yaml"],
        start_path=f"himena-{datetime_str}.session.yaml",
        group="session",
    ):
        return ui.save_session(path, allow_calculate=allow_calc)
    raise Cancelled


@ACTIONS.append_from_fn(
    id="save-session-stand-alone",
    title="Save Session (Stand-along) ...",
    menus=[{"id": MenuId.FILE_SESSION, "group": WRITE_GROUP}],
    enablement=_ctx.num_tabs > 0,
)
def save_session_stand_along_from_dialog(ui: MainWindow) -> None:
    datetime_str = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    if path := ui.exec_file_dialog(
        mode="w",
        extension_default=".session.zip",
        allowed_extensions=[".session.zip"],
        start_path=f"himena-{datetime_str}.session.zip",
        group="session",
    ):
        return ui.save_session_stand_alone(path)
    return Cancelled


@ACTIONS.append_from_fn(
    id="save-tab-session",
    title="Save Tab Session ...",
    menus=[{"id": MenuId.FILE_SESSION, "group": WRITE_GROUP}],
    enablement=(_ctx.num_tabs > 0) & (_ctx.num_sub_windows > 0),
)
def save_tab_session_from_dialog(ui: MainWindow) -> None:
    """Save current application state to a session."""
    datetime_str = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    if path := ui.exec_file_dialog(
        mode="w",
        extension_default=".session.yaml",
        allowed_extensions=[".session.yaml"],
        start_path=f"Tab-{datetime_str}.session.yaml",
        group="session",
    ):
        if tab := ui.tabs.current():
            return tab.save_session(path)
    raise Cancelled


@ACTIONS.append_from_fn(
    id="quit",
    title="Quit",
    menus=[{"id": MenuId.FILE, "group": EXIT_GROUP}],
    keybindings=[StandardKeyBinding.Quit],
    recording=False,
)
def quit_main_window(ui: MainWindow) -> None:
    """Quit the application."""
    ui._backend_main_window._exit_main_window(confirm=True)


@ACTIONS.append_from_fn(
    id="copy-screenshot",
    title="Copy screenshot of entire main window",
    menus=[{"id": MenuId.FILE_SCREENSHOT, "group": COPY_SCR_SHOT}],
)
def copy_screenshot(ui: MainWindow) -> ClipboardDataModel:
    """Copy a screenshot of the main window to the clipboard."""
    data = ui._backend_main_window._screenshot("main")
    return ClipboardDataModel(image=data)


@ACTIONS.append_from_fn(
    id="copy-screenshot-area",
    title="Copy screenshot of tab area",
    menus=[{"id": MenuId.FILE_SCREENSHOT, "group": COPY_SCR_SHOT}],
    enablement=_ctx.num_tabs > 0,
)
def copy_screenshot_area(ui: MainWindow) -> ClipboardDataModel:
    """Copy a screenshot of the tab area to the clipboard."""
    data = ui._backend_main_window._screenshot("area")
    return ClipboardDataModel(image=data)


@ACTIONS.append_from_fn(
    id="copy-screenshot-window",
    title="Copy Screenshot of sub-window",
    menus=[{"id": MenuId.FILE_SCREENSHOT, "group": COPY_SCR_SHOT}],
    enablement=_ctx.num_sub_windows > 0,
)
def copy_screenshot_window(ui: MainWindow) -> ClipboardDataModel:
    """Copy a screenshot of the sub window to the clipboard."""
    data = ui._backend_main_window._screenshot("window")
    return ClipboardDataModel(image=data)


@ACTIONS.append_from_fn(
    id="settings",
    title="Settings ...",
    menus=[{"id": MenuId.FILE, "group": SETTINGS_GROUP}],
    keybindings=[KeyBindingRule(primary=KeyMod.CtrlCmd | KeyCode.Comma)],
)
def show_setting_dialog(ui: MainWindow):
    """Open a dialog to edit the application profile."""
    from himena.qt.settings import QSettingsDialog

    return QSettingsDialog(ui).exec()


def _save_screenshot(ui: MainWindow, target: str) -> None:
    from PIL import Image
    import numpy as np

    arr = ui._backend_main_window._screenshot(target)
    save_path = ui.exec_file_dialog(
        mode="w",
        extension_default=".png",
        start_path="Screenshot.png",
        group="screenshot",
    )
    if save_path is None:
        raise Cancelled
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
    submenu=MenuId.FILE_SESSION,
    title="Session",
    group=READ_GROUP,
)
SUBMENUS.append_from(
    id=MenuId.FILE,
    submenu=MenuId.FILE_SCREENSHOT,
    title="Screenshot",
    group=SCR_SHOT_GROUP,
)
