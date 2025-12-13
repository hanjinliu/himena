from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from contextlib import contextmanager
from logging import getLogger
from pathlib import Path
import threading
import uuid
from typing import (
    Any,
    Callable,
    Sequence,
    Generic,
    Iterator,
    Literal,
    TypeVar,
    overload,
    TYPE_CHECKING,
)
import warnings
from app_model.expressions import create_context
from psygnal import SignalGroup, Signal

from himena import _providers
from himena._app_model import AppContext, HimenaApplication
from himena._open_recent import RecentFileManager, RecentSessionManager
from himena._utils import get_widget_class_id, import_object
from himena.consts import NO_RECORDING_FIELD
from himena.plugins import _checker, actions as _actions
from himena.profile import AppProfile, load_app_profile
from himena.style import Theme
from himena.standards import BaseMetadata
from himena.types import (
    ClipboardDataModel,
    FutureInfo,
    Size,
    UseDockWidget,
    UseTab,
    WidgetDataModel,
    NewWidgetBehavior,
    DockArea,
    DockAreaString,
    BackendInstructions,
    WindowRect,
)
from himena.utils.misc import is_subtype, is_url_string, fetch_text_from_url, norm_paths
from himena.widgets._backend import BackendMainWindow
from himena.widgets._keyset import KeySet
from himena.widgets._hist import HistoryContainer, FileDialogHistoryDict
from himena.widgets._initialize import remove_instance
from himena.widgets._typemap import ObjectTypeMap, register_defaults
from himena.widgets._widget_list import TabList, TabArea, DockWidgetList
from himena.widgets._wrapper import ParametricWindow, SubWindow, DockWidget
from himena.workflow import ProgrammaticMethod, ActionHintRegistry
from himena._socket import SocketInfo

if TYPE_CHECKING:
    from app_model.types import KeyBindingRule
    from app_model.expressions import BoolOp
    from himena.widgets._widget_list import PathOrPaths
    from himena.workflow import ModelParameter, WindowParameter
    from IPython.lib.pretty import RepresentationPrinter

_W = TypeVar("_W")  # backend widget type
_T = TypeVar("_T")  # internal data type
_F = TypeVar("_F")  # function type
_LOGGER = getLogger(__name__)


class MainWindowEvents(SignalGroup, Generic[_W]):
    """Main window events."""

    tab_activated = Signal(TabArea[_W])
    window_activated = Signal(SubWindow[_W])
    window_added = Signal(SubWindow[_W])
    window_closed = Signal(SubWindow[_W])


class MainWindow(Generic[_W]):
    """The main window handler object."""

    def __init__(
        self,
        backend: BackendMainWindow[_W],
        app: HimenaApplication,  # must be initialized
        theme: Theme,
    ) -> None:
        from himena.widgets._initialize import set_current_instance

        self._events = MainWindowEvents()
        self._backend_main_window = backend
        self._internal_clipboard_data: Any | None = None
        self._tab_list = TabList(backend)
        self._new_widget_behavior = NewWidgetBehavior.WINDOW
        self._model_app = app
        self._instructions = BackendInstructions()
        self._history_tab = HistoryContainer[int](max_size=20)
        self._history_command = HistoryContainer[str](max_size=200)
        self._history_closed = HistoryContainer[tuple[Path, str | None]](max_size=10)
        self._file_dialog_hist = FileDialogHistoryDict()
        app.commands.executed.connect(self._on_command_execution)
        backend._connect_main_window_signals(self)
        self._ctx_keys = AppContext(create_context(self, max_depth=0))
        self._tab_list.changed.connect(backend._update_context)
        self._dock_widget_list = DockWidgetList(backend)
        self._recent_manager = RecentFileManager.default(app)
        self._recent_session_manager = RecentSessionManager.default(app)
        if "." not in app.name:
            # likely a mock instance
            set_current_instance(app.name, self)
            self._recent_manager.update_menu()
            self._recent_session_manager.update_menu()
        self._executor = ThreadPoolExecutor(max_workers=5)
        self._global_lock = threading.Lock()
        self._object_type_map = ObjectTypeMap()
        self.theme = theme
        register_defaults(self._object_type_map)

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}(tabs={self.tabs}, dock_widgets={self.dock_widgets})"
        )

    def _repr_pretty_(self, p: RepresentationPrinter, cycle: bool):
        if cycle:
            p.text(f"{type(self).__name__}(...)")
        else:
            p.text(f"{type(self).__name__}(\n")
            p.text("  tabs=")
            p.pretty(self.tabs)
            p.text(",\n")
            p.text("  dock_widgets=")
            p.pretty(self.dock_widgets)
            p.text(",\n")
            p.text(")")

    @property
    def events(self) -> MainWindowEvents[_W]:
        """Main window events."""
        return self._events

    @property
    def object_type_map(self) -> ObjectTypeMap:
        """Mapping object to string that describes the type."""
        return self._object_type_map

    @property
    def action_hint_registry(self) -> ActionHintRegistry:
        """Action hint registry."""
        return _actions.AppActionRegistry.instance()._action_hint_reg

    @property
    def socket_info(self) -> SocketInfo:
        """Socket information."""
        eh = self._backend_main_window._event_loop_handler
        return SocketInfo(host=eh._host, port=eh._port)

    @property
    def keys(self) -> KeySet:
        """Get the set of currently pressed keys."""
        return KeySet(self)

    @property
    def theme(self) -> Theme:
        """Get the current color theme of the main window."""
        return self._theme

    @theme.setter
    def theme(self, theme: str | Theme) -> None:
        """Set the style of the main window."""
        if isinstance(theme, str):
            theme = Theme.from_global(theme)
        self._theme = theme
        self._backend_main_window._update_widget_theme(theme)

        # if child implements "theme_changed_callback", call it
        for win in self.iter_windows():
            _checker.call_theme_changed_callback(win.widget, theme)
        for dock in self.dock_widgets:
            _checker.call_theme_changed_callback(dock.widget, theme)
        return None

    @property
    def app_profile(self) -> AppProfile:
        """Get the current application profile object."""
        return load_app_profile(self._model_app.name)

    def submit_async_task(
        self,
        func: Callable,
        *args,
        progress_description: str | None = None,
        **kwargs,
    ) -> Future:
        """Submit a task to the thread pool.

        Parameters
        ----------
        func : callable
            Function to run in the background.
        progress_description : str, optional
            Description of the task in the progress bar.
        """
        future = self._executor.submit(func, *args, **kwargs)
        if progress_description is None:
            progress_description = f"Running {func!r}"
        self._backend_main_window._add_job_progress(
            future, desc=progress_description, total=0
        )
        self.model_app.injection_store.process(future)
        return future

    @property
    def tabs(self) -> TabList[_W]:
        """Tab list object."""
        return self._tab_list

    def windows_for_type(self, types: str | list[str]) -> list[SubWindow[_W]]:
        """Get all sub-windows for the given types."""
        windows = []
        if isinstance(types, str):
            types = [types]
        if tab := self.tabs.current():
            for win in tab:
                mtype = win.model_type()
                if mtype and any(is_subtype(mtype, t) for t in types):
                    windows.append(win)
        return windows

    @property
    def dock_widgets(self) -> DockWidgetList[_W]:
        """Dock widget list object."""
        return self._dock_widget_list

    @property
    def model_app(self) -> HimenaApplication:
        """The app-model application instance."""
        return self._model_app

    @property
    def area_size(self) -> tuple[int, int]:
        """(width, height) of the main window tab area."""
        return self._backend_main_window._area_size()

    @property
    def rect(self) -> WindowRect:
        """Window rect (left, top, width, height) of the main window."""
        return self._backend_main_window._main_window_rect()

    @rect.setter
    def rect(self, value) -> None:
        rect = WindowRect.from_tuple(*value)
        return self._backend_main_window._set_main_window_rect(rect)

    @property
    def size(self) -> Size:
        """Size (width, height) of the main window."""
        return self.rect.size()

    @size.setter
    def size(self, size) -> None:
        r0 = self.rect
        s0 = Size(*size)
        self.rect = WindowRect(r0.left, r0.top, s0.width, s0.height)

    @property
    def clipboard(self) -> ClipboardDataModel | None:
        """Get the clipboard data as a ClipboardDataModel instance."""
        model = self._backend_main_window._clipboard_data()
        model.internal_data = self._internal_clipboard_data
        return model

    @clipboard.setter
    def clipboard(self, data: str | ClipboardDataModel) -> None:
        """Set the clipboard data."""
        if isinstance(data, str):
            data = ClipboardDataModel(text=data)
        elif not isinstance(data, ClipboardDataModel):
            raise ValueError("Clipboard data must be a ClipboardDataModel instance.")
        _LOGGER.info("Setting clipboard data: %r", data)
        self._backend_main_window._set_clipboard_data(data)
        self._internal_clipboard_data = data.internal_data

    def set_clipboard(
        self,
        *,
        text: str | None = None,
        html: str | None = None,
        image: Any | None = None,
        files: list[str | Path] | None = None,
        internal_data: Any | None = None,
    ) -> None:
        """Set clipboard data."""
        self.clipboard = ClipboardDataModel(
            text=text,
            html=html,
            image=image,
            files=files or [],
            internal_data=internal_data,
        )

    def add_tab(self, title: str | None = None) -> TabArea[_W]:
        """Add a new tab of given name."""
        return self.tabs.add(title)

    def window_for_id(self, identifier: uuid.UUID) -> SubWindow[_W] | None:
        """Retrieve a sub-window by its identifier."""
        if not isinstance(identifier, uuid.UUID):
            raise ValueError(f"Expected UUID, got {identifier!r}.")
        for win in self.iter_windows():
            if win._identifier == identifier:
                return win

    def _window_for_workflow_id(self, identifier: uuid.UUID) -> SubWindow[_W] | None:
        """Retrieve a sub-window by its workflow identifier."""
        for win in self.iter_windows():
            try:
                last_id = win._widget_workflow.last_id()
            except Exception:
                return None
            if last_id == identifier:
                return win

    def add_widget(
        self,
        widget: _W,
        *,
        title: str | None = None,
    ) -> SubWindow[_W]:
        """Add a widget to the sub window.

        Any widget that can be interpreted by the backend can be added. For example, for
        Qt application, you can add any QWidget instance:

        ```python
        ui.add_widget(QtW.QLabel("Hello world!"), title="my widget!")
        ```

        Parameters
        ----------
        widget : Any
            Widget to add.
        title : str, optional
            Title of the sub-window. If not given, its name will be automatically
            generated.

        Returns
        -------
        SubWindow
            The sub-window handler.
        """
        return _tab_to_be_used(self).add_widget(widget, title=title)

    def add_dock_widget(
        self,
        widget: _W,
        *,
        title: str | None = None,
        area: DockAreaString | DockArea | None = DockArea.RIGHT,
        allowed_areas: list[DockAreaString | DockArea] | None = None,
        _identifier: uuid.UUID | None = None,
    ) -> DockWidget[_W]:
        """Add a custom widget as a dock widget of the main window.

        Parameters
        ----------
        widget : Widget type
            Widget instance that is allowed for the backend.
        title : str, optional
            Title of the dock widget.
        area : dock area, default DockArea.RIGHT
            String or DockArea enum that describes where the dock widget initially
            appears.
        allowed_areas : list of dock area, optional
            List of allowed dock areas for the widget.

        Returns
        -------
        DockWidget
            The dock widget handler.
        """
        dock = DockWidget(widget, self._backend_main_window, identifier=_identifier)
        dock_native = dock._split_interface_and_frontend()[1]
        self._backend_main_window.add_dock_widget(
            dock_native, title=title, area=area, allowed_areas=allowed_areas
        )
        self._dock_widget_list._add_dock_widget(dock)
        _checker.call_widget_added_callback(widget)
        _checker.call_theme_changed_callback(widget, self.theme)
        return dock

    def add_object(
        self,
        value: Any,
        *,
        type: str | None = None,
        title: str | None = None,
        force_open_with: str | None = None,
        metadata: Any | None = None,
    ) -> SubWindow[_W]:
        """Add any data as a widget data model.

        CAUTION: result of this method may not be stable between different sessions. If
        type is not given, the application will look for the proper widget data type in
        the type map. If this type map was modified, the result will be different.

        Parameters
        ----------
        value : Any
            Any object. Whether it can be represented as a widget is dependent on the
            plugins that are installed.
        type : str, optional
            Any str that describes the type of the object. This type must be registered
            with a proper widget class.
        title : str, optional
            Title of the sub-window.

        Returns
        -------
        SubWindow
            The sub-window handler.
        """
        if type is None:
            if isinstance(metadata, BaseMetadata):
                type = metadata.expected_type()
        if type is None:
            type, value, metadata_fallback = self._object_type_map.pick_type(value)
            if metadata is None:
                metadata = metadata_fallback
        wd = WidgetDataModel(
            value=value,
            type=type,
            title=title,
            force_open_with=force_open_with,
            metadata=metadata,
            workflow=ProgrammaticMethod(output_model_type=type).construct_workflow(),
        )
        return self.add_data_model(wd)

    def add_data_model(self, model: WidgetDataModel) -> SubWindow[_W] | DockWidget[_W]:
        """Add a widget data model as a widget."""
        if not isinstance(model, WidgetDataModel):
            raise TypeError(
                f"input model must be an instance of WidgetDataModel, got {model!r}"
            )
        if len(model.workflow) == 0:
            # this case may happen if this method was programatically called
            wf = ProgrammaticMethod(output_model_type=model.type).construct_workflow()
            model = model.model_copy(update={"workflow": wf})
        self.set_status_tip(f"Data model {model.title!r} added.", duration=1)
        widget = self._pick_widget(model)
        if isinstance(_use_dock := model.output_window_type, UseDockWidget):
            sub_win = self.add_dock_widget(
                widget,
                title=model.title,
                area=_use_dock.area,
                allowed_areas=_use_dock.allowed_areas,
            )
        elif isinstance(model.output_window_type, UseTab):
            tab_area = self.tabs.add(model.title)
            sub_win = tab_area.add_widget(widget, title=model.title)
            sub_win._update_from_returned_model(model)
            tab_area._mark_as_single_window_mode()
            if model.extension_default is not None:
                sub_win._extension_default_fallback = model.extension_default
        else:  # pragma: no cover
            sub_win = _tab_to_be_used(self).add_data_model(model)
        return sub_win

    def add_function(
        self,
        func: Callable[..., _T],
        *,
        preview: bool = False,
        title: str | None = None,
        show_parameter_labels: bool = True,
        auto_close: bool = True,
        run_async: bool = False,
        result_as: Literal["window", "below", "right"] = "window",
    ) -> ParametricWindow[_W]:
        """Add a function as a parametric sub-window.

        The input function must return a `WidgetDataModel` instance, which can be
        interpreted by the application.

        Parameters
        ----------
        func : function (...) -> WidgetDataModel
            Function that generates a model from the input parameters.
        title : str, optional
            Title of the sub-window.

        Returns
        -------
        SubWindow
            The sub-window instance that represents the output model.
        """
        return _tab_to_be_used(self).add_function(
            func, title=title, preview=preview, result_as=result_as,
            show_parameter_labels=show_parameter_labels, auto_close=auto_close,
            run_async=run_async,
        )  # fmt: skip

    def add_parametric_widget(
        self,
        widget: _W,
        callback: Callable | None = None,
        *,
        title: str | None = None,
        preview: bool = False,
        auto_close: bool = True,
        auto_size: bool = True,
        run_async: bool = False,
        result_as: Literal["window", "below", "right"] = "window",
    ) -> ParametricWindow[_W]:
        return _tab_to_be_used(self).add_parametric_widget(
            widget, callback, title=title, preview=preview, auto_close=auto_close,
            auto_size=auto_size, result_as=result_as, run_async=run_async,
        )  # fmt: skip

    def read_file(
        self,
        file_path: PathOrPaths,
        plugin: str | None = None,
    ) -> SubWindow[_W]:
        """Read local file(s) and open as a new sub-window in this tab.

        Parameters
        ----------
        file_path : str or Path or list of them
            Path(s) to the file to read. If a list is given, they will be read as a
            group, not as separate windows.
        plugin : str, optional
            If given, reader provider will be searched with the plugin name. This value
            is usually the full import path to the reader provider function, such as
            `"himena_builtins.io.default_reader_provider"`.

        Returns
        -------
        SubWindow
            The sub-window instance that is constructed based on the return value of
            the reader.
        """
        return self.read_files([file_path], plugin=plugin)[0]

    def read_files(
        self,
        file_paths: PathOrPaths,
        plugin: str | None = None,
    ) -> list[SubWindow[_W]]:
        """Read multiple files and open as new sub-windows in this tab."""
        models = self._paths_to_models(file_paths, plugin=plugin)
        out = [self.add_data_model(model) for model in models]
        if len(out) == 1:
            self.set_status_tip(f"File opened: {out[0].title}", duration=5)
        elif len(out) > 1:
            _titles = ", ".join(w.title for w in out)
            self.set_status_tip(f"File opened: {_titles}", duration=5)
        return out

    def _paths_to_models(self, file_paths: PathOrPaths, plugin: str | None = None):
        ins = _providers.ReaderStore.instance()
        file_paths = norm_paths(file_paths)
        reader_path_sets = [
            (ins.pick(file_path, plugin=plugin), file_path) for file_path in file_paths
        ]
        models = [
            reader.read_and_update_source(file_path)
            for reader, file_path in reader_path_sets
        ]
        self._recent_manager.append_recent_files(
            [(fp, reader.plugin_str) for reader, fp in reader_path_sets]
        )
        return models

    def read_files_async(
        self,
        file_paths: PathOrPaths,
        plugin: str | None = None,
    ) -> Future:
        """Read multiple files asynchronously and return a future."""
        file_paths = norm_paths(file_paths)
        future = self._executor.submit(self._paths_to_models, file_paths, plugin=plugin)
        if len(file_paths) == 1:
            self.set_status_tip(f"Opening: {file_paths[0].as_posix()}", duration=5)
        else:
            self.set_status_tip(f"Opening {len(file_paths)} files", duration=5)
        FutureInfo(list[WidgetDataModel]).set(future)  # set info for injection store
        return future

    def run_script(self, file: str | Path) -> Any:
        """Run the main function of the given script file with this UI instance."""
        reg = _actions.AppActionRegistry.instance()
        num_actions_before = len(reg._actions)
        if is_url_string(file):
            code = fetch_text_from_url(file)
            filename = "<remote>"
        else:
            filepath = Path(file).resolve()
            code = filepath.read_text()
            filename = str(filepath)
        compiled = compile(code, filename, "exec")
        glob = {}
        loc = {}
        exec(compiled, glob, loc)
        if callable(main := loc.get("main", None)):
            main.__globals__.update(loc)
            out = main(self)
        else:
            out = None
        num_actions_after = len(reg._actions)
        if num_actions_after != num_actions_before:
            # need rebuild
            warnings.warn(
                "Registering plugins after application launch is not fully supported.",
                UserWarning,
                stacklevel=1,
            )
        return out

    def load_session(self, path: str | Path) -> None:
        """Read a session file and update the main window based on the content."""
        from himena.session import update_from_zip, update_from_directory

        fp = Path(path)
        if fp.suffix == ".zip":
            update_from_zip(self, fp)
        elif fp.is_dir():
            update_from_directory(self, fp)
        else:
            raise ValueError(f"Session must be a zip file or a directory, got {fp}.")
        # always plugin=None for reading a session file as a session
        self._recent_session_manager.append_recent_files([(fp, None)])
        self.set_status_tip(f"Session loaded: {fp}", duration=5)

    def save_session(
        self,
        path: str | Path,
        *,
        save_copies: bool = False,
        allow_calculate: Sequence[str] = (),
    ) -> None:
        """Save the current session to a zip file as a stand-along file."""
        from himena.session import dump_zip, dump_directory

        path = Path(path)
        if path.suffix == ".zip":
            dump_zip(
                self, path, save_copies=save_copies, allow_calculate=allow_calculate
            )
        else:
            dump_directory(
                self, path, save_copies=save_copies, allow_calculate=allow_calculate
            )
        self.set_status_tip(f"Session saved to {path}")
        self._recent_session_manager.append_recent_files([(path, None)])

    def clear(self) -> None:
        """Clear all widgets in the main window."""
        self.tabs.clear()
        self.dock_widgets.clear()

    def set_status_tip(
        self,
        text: str,
        duration: float = 10.0,
        process_event: bool = False,
    ) -> None:
        """Set the status tip of the main window.

        This method can be safely called from any thread.

        Parameters
        ----------
        text : str
            Text to show in the status bar.
        duration : float, default 10.0
            Duration (seconds) to show the status tip.
        process_event : bool, default False
            If True, the application will process events after setting the status tip.
        """
        self._backend_main_window._set_status_tip(text, duration)
        if process_event:
            self._backend_main_window._event_loop_handler.process_events()

    def show_notification(self, text: str, duration: float = 5.0) -> None:
        """Show a temporary notification in the main window.

        Parameters
        ----------
        text : str
            Text to show in the notification.
        duration : float, default 5.0
            Duration (seconds) to show the notification.
        """
        self._backend_main_window._show_notification(text, duration)

    def show_tooltip(
        self,
        text: str,
        duration: float = 3.0,
        behavior: Literal["stay", "follow", "until_move"] = "follow",
    ) -> None:
        """Show a temporary tooltip next to the cursor in the main window.

        Parameters
        ----------
        text : str
            HTML text to show in the tooltip.
        duration : float, default 3.0
            Duration (seconds) to show the tooltip.
        behavior : str, default "follow"
            Behavior of the tooltip. "stay" to show at the position where it is created,
            "follow" to follow the cursor, "until_move" to show until the cursor moves.
        """
        self._backend_main_window._show_tooltip(text, duration, behavior)

    @overload
    def register_function(
        self,
        func: None = None,
        *,
        menus: str | Sequence[str] = "plugins",
        title: str | None = None,
        types: str | Sequence[str] | None = None,
        enablement: BoolOp | None = None,
        keybindings: Sequence[KeyBindingRule] | None = None,
        command_id: str | None = None,
    ) -> None: ...  # noqa: E501
    @overload
    def register_function(
        self,
        func: _F,
        *,
        menus: str | Sequence[str] = "plugins",
        title: str | None = None,
        types: str | Sequence[str] | None = None,
        enablement: BoolOp | None = None,
        keybindings: Sequence[KeyBindingRule] | None = None,
        command_id: str | None = None,
    ) -> _F: ...  # noqa: E501

    def register_function(
        self,
        func=None,
        *,
        menus="plugins",
        title=None,
        types=None,
        enablement=None,
        keybindings=None,
        command_id=None,
    ):
        """Register a function as a callback in runtime.

        Example
        -------
        ``` python
        @ui.register_function(menus="plugins", title="Test functions)
        def test_function():
            print("test")
        ```

        Parameters
        ----------
        func : callable, optional
            Function to register as an action.
        menus : str or sequence of str, default "plugins"
            Menu(s) to add the action. Submenus are separated by `/`.
        title : str, optional
            Title of the action. Name of the function will be used if not given.
        types: str or sequence of str, optional
            The `type` parameter(s) allowed as the WidgetDataModel. If this parameter
            is given, action will be grayed out if the active window does not satisfy
            the listed types.
        enablement: Expr, optional
            Expression that describes when the action will be enabled. As this argument
            is a generalized version of `types` argument, you cannot use both of them.
        command_id : str, optional
            Command ID. If not given, the function qualname will be used.
        """

        def _inner(f):
            action = _actions.make_action_for_function(
                f,
                menus=menus,
                title=title,
                types=types,
                enablement=enablement,
                keybindings=keybindings,
                command_id=command_id,
            )
            _actions.AppActionRegistry.instance().add_action(action)
            added_menus = _actions.AppActionRegistry.instance().install_to(
                self.model_app, [action]
            )
            self._backend_main_window._rebuild_for_runtime(added_menus)
            return f

        return _inner(func) if func else _inner

    def exec_action(
        self,
        id: str,
        *,
        model_context: WidgetDataModel | None = None,
        window_context: SubWindow | None = None,
        with_params: dict[str, Any] | None = None,
        with_defaults: dict[str, Any] | None = None,
        process_model_output: bool = True,
    ) -> Any:
        """Execute an action by its ID.

        Parameters
        ----------
        id : str
            Action ID.
        model_context : WidgetDataModel, optional
            If given, this model will override the application context for the type
            `WidgetDataModel` before the execution.
        window_context : SubWindow, optional
            If given, this window will override the application context for the type
            `SubWindow` before the execution.
        with_params : dict, optional
            Parameters to pass to the parametric action. These parameters will directly
            be passed to the parametric window created after the action is executed.
        with_defaults : dict, optional
            If given, the resulting parametric window will be updated with these values.
        process_model_output : bool, default True
            If True, the output result will be processed by the application context. If
            the command return a `WidgetDataModel` instance, it will be converted to a
            sub-window.
        """
        if with_params is not None and with_defaults is not None:
            raise TypeError(
                "Cannot use both `with_params` and `with_defaults` at the same time."
            )
        providers: list[tuple[Any, type]] = []
        if model_context is not None:
            providers.append((model_context, WidgetDataModel, 1000))
        if window_context is not None:
            if isinstance(window_context, SubWindow):
                _window_context = window_context
            else:
                raise TypeError(
                    f"`window_context` must be SubWindow or UUID, got {window_context}"
                )
            providers.append((_window_context, SubWindow, 1000))
            if model_context is None and _window_context.supports_to_model:
                providers.append((_window_context.to_model(), WidgetDataModel, 100))
        # execute the command under the given context
        with (
            self.model_app.injection_store.register(providers=providers),
            self._execute_in_context(
                is_gui=with_params is None, process_model_output=process_model_output
            ),
        ):
            result = self.model_app.commands.execute_command(id).result()
            if with_params is not None:
                if (tab := self.tabs.current()) is not None and len(tab) > 0:
                    param_widget = tab[-1]
                else:  # pragma: no cover
                    raise RuntimeError("Unreachable code.")
                if not isinstance(param_widget, ParametricWindow):
                    if len(with_params) == 0:
                        if isinstance(result, Future):
                            return result.result()  # or appropriate handling
                        return result
                    raise ValueError(
                        f"Parametric widget expected but got {param_widget}."
                    )
                # run the callback with the given parameters synchronously
                result = param_widget._callback_with_params(
                    with_params,
                    force_sync=True,
                    force_close=True,
                )
            elif with_defaults is not None:
                if (tab := self.tabs.current()) is not None and len(tab) > 0:
                    param_widget = tab[-1]
                else:  # pragma: no cover
                    raise ValueError(
                        f"Command {id!r} did not create a parametric window."
                    )
                if not isinstance(param_widget, ParametricWindow):
                    if with_defaults:
                        raise ValueError(
                            f"Parametric widget expected but got {param_widget}."
                        )
                else:
                    param_widget.update_params(with_defaults)
        if (
            isinstance(result, WidgetDataModel)
            and result.update_inplace
            and isinstance(window_context, SubWindow)
        ):
            # Need to update the current window if this method is called with a wrong
            # window focus.
            self.current_window = window_context
        return result

    @overload
    def exec_choose_one_dialog(
        self,
        title: str,
        message: str,
        choices: list[tuple[str, _T]],
        how: Literal["buttons", "radiobuttons"] = "buttons",
    ) -> _T | None: ...
    @overload
    def exec_choose_one_dialog(
        self,
        title: str,
        message: str,
        choices: list[str],
        how: Literal["buttons", "radiobuttons"] = "buttons",
    ) -> str | None: ...

    def exec_choose_one_dialog(self, title, message, choices, how="buttons"):
        """Execute a dialog to choose one from the given choices.

        Parameters
        ----------
        title : str
            Window title of the dialog.
        message : str
            HTML Message to show in the dialog.
        choices : list
            List of choices. Each choice can be a string or a tuple of (text, value).
            This method will return the selected value.
        how : str, default "buttons"
            How to show the choices. "buttons" for horizontal buttons, "radiobuttons"
            for vertically arranged radio buttons.
        """
        if res := self._instructions.choose_one_dialog_response:
            return res()
        _choices_normed = []
        for choice in choices:
            if isinstance(choice, str):
                _choices_normed.append((choice, choice))
            else:
                text, value = choice
                _choices_normed.append((text, value))
        return self._backend_main_window._request_choice_dialog(
            title, message, _choices_normed, how=how
        )

    @overload
    def exec_file_dialog(
        self,
        mode: Literal["r", "d", "w"] = "r",
        *,
        extension_default: str | None = None,
        allowed_extensions: list[str] | None = None,
        caption: str | None = None,
        start_path: str | Path | None = None,
        group: str | None = None,
    ) -> Path | None: ...
    @overload
    def exec_file_dialog(
        self,
        mode: Literal["rm"],
        *,
        extension_default: str | None = None,
        allowed_extensions: list[str] | None = None,
        caption: str | None = None,
        start_path: str | Path | None = None,
        group: str | None = None,
    ) -> list[Path] | None: ...

    def exec_file_dialog(
        self,
        mode: Literal["r", "d", "w", "rm"] = "r",
        *,
        extension_default=None,
        allowed_extensions=None,
        caption=None,
        start_path=None,
        group: str | None = None,
    ):
        """Execute a file dialog to get file path(s)."""
        if mode not in {"r", "d", "w", "rm"}:
            raise ValueError(f"`mode` must be 'r', 'd', 'w' or 'rm', got {mode!r}.")
        if res := self._instructions.file_dialog_response:
            return res()
        if group is None:
            group = mode

        if mode == "w":
            if start_path is None:
                _start_path = self._file_dialog_hist.get_path(group)
            elif Path(start_path).parent != Path("."):
                _start_path = Path(start_path)
            else:  # filename only is given
                _start_path = self._file_dialog_hist.get_path(group, str(start_path))
        else:
            _start_path = Path(start_path or self._file_dialog_hist.get_path(group))
        result = self._backend_main_window._open_file_dialog(
            mode,
            extension_default=extension_default,
            allowed_extensions=allowed_extensions,
            caption=caption,
            start_path=_start_path,
        )
        if result is None:
            return None
        if mode in ["r", "w", "d"]:
            self._file_dialog_hist.update(group, result.parent)
        elif result:
            self._file_dialog_hist.update(group, result[0].parent)
        return result

    def show(self, run: bool = False) -> None:
        """
        Show the main window.

        Parameters
        ----------
        run : bool, default False
            If True, run the application event loop.
        """
        self._backend_main_window.show(run)

    def close(self) -> None:
        """Close the main window."""
        self._backend_main_window._exit_main_window(confirm=False)
        remove_instance(self.model_app.name, self)

    @property
    def current_window(self) -> SubWindow[_W] | None:
        """Get the current sub-window."""
        idx_tab = self._backend_main_window._current_tab_index()
        if idx_tab is None:
            return None
        idx_win = self._backend_main_window._current_sub_window_index(idx_tab)
        if idx_win is None:
            return None
        return self.tabs[idx_tab][idx_win]

    @current_window.setter
    def current_window(self, win: SubWindow[_W] | None) -> None:
        """Set the current sub-window."""
        _main = self._backend_main_window
        if win is None:
            _main._set_current_tab_index(None)
            i_tab = _main._current_tab_index()
            if i_tab is not None:
                _main._set_current_sub_window_index(i_tab, None)
        else:
            for i_tab, tab in self.tabs.enumerate():
                for i_win, sub in tab.enumerate():
                    if sub is win:
                        _main._set_current_tab_index(i_tab)
                        _main._set_current_sub_window_index(i_tab, i_win)
                        return None

    @property
    def current_model(self) -> WidgetDataModel | None:
        """Get the current model of the active sub-window."""
        if sub := self.current_window:
            return sub.to_model()

    def iter_windows(self) -> Iterator[SubWindow[_W]]:
        """Iterate over all the sub-windows in this main window."""
        for tab in self.tabs:
            yield from tab

    def _tab_activated(self, i: int):
        if i < 0:
            return None
        tab = self.tabs.get(i)
        if tab is not None:
            self.events.tab_activated.emit(tab)
            self._main_window_resized(self.area_size)  # update layout and anchor
        if self._history_tab.get_from_last(1) != i:
            self._history_tab.add(i)

    def move_window(self, sub: SubWindow[_W], target_index: int) -> None:
        """Move the sub-window to the target tab index."""
        i_tab = i_win = None
        for _i_tab, tab in self.tabs.enumerate():
            for _i_win, win in tab.enumerate():
                if win is sub:
                    i_tab = _i_tab
                    i_win = _i_win
                    break

        if i_tab is None or i_win is None or target_index == i_tab:
            return None
        title = self.tabs[i_tab][i_win].title
        old_rect = self.tabs[i_tab][i_win].rect
        win, widget = self.tabs[i_tab]._pop_no_emit(i_win)
        if target_index < 0:
            self.add_tab()
        self.tabs[target_index].append(win, title)
        win.rect = old_rect
        if layout := win._parent_layout_ref():
            layout.remove(win)
        self.tabs.current_index = i_tab

    def _window_activated(self):
        back = self._backend_main_window
        back._update_context()
        i_tab = back._current_tab_index()
        if i_tab is None:
            return back._update_control_widget(None)
        tab = self.tabs.get(i_tab)
        if tab is None or len(tab) == 0:
            return back._update_control_widget(None)
        i_win = back._current_sub_window_index(i_tab)
        if i_win is None or len(tab) <= i_win:
            return back._update_control_widget(None)
        win = tab[i_win]
        back._update_control_widget(win.widget)
        _checker.call_widget_activated_callback(win.widget)
        self.events.window_activated.emit(win)

    def _main_window_resized(self, size: Size):
        if tab := self.tabs.current():
            for layout in tab.layouts:
                layout.anchor = layout.anchor.update_for_window_rect(size, layout.rect)
                layout._reanchor(size)
            for win in tab:
                win.anchor = win.anchor.update_for_window_rect(size, win.rect)
                win._reanchor(size)

    @contextmanager
    def _execute_in_context(
        self,
        is_gui: bool = False,
        process_model_output: bool = True,
        unwrap_future: bool = True,
    ):
        with self._global_lock:
            old_inst = self._instructions.model_copy()
            self._instructions = self._instructions.updated(
                gui_execution=is_gui,
                process_model_output=process_model_output,
                unwrap_future=unwrap_future,
            )
            try:
                yield None
            finally:
                self._instructions = old_inst

    def _iter_widget_class(self, model: WidgetDataModel) -> Iterator[type[_W]]:
        """Pick the most suitable widget class for the given model."""
        if model.force_open_with:
            yield import_object(model.force_open_with)
            return
        widget_classes, fallback_class = self._backend_main_window._list_widget_class(
            model.type
        )
        if not widget_classes:
            warnings.warn(
                f"No widget class is registered for model type {model.type!r}.",
                RuntimeWarning,
                stacklevel=2,
            )
            yield fallback_class
            return
        complete_match = [
            (tup.priority, tup.widget_class)
            for tup in widget_classes
            if tup.type == model.type and tup.priority >= 0
        ]
        if complete_match:
            yield from _iter_sorted(complete_match)
        subtype_match = [
            ((tup.type.count("."), tup.priority), tup.widget_class)
            for tup in widget_classes
            if tup.priority >= 0
        ]
        yield from _iter_sorted(subtype_match)

    def _pick_widget(self, model: WidgetDataModel) -> _W:
        """Pick the most suitable widget for the given model."""
        exceptions: list[tuple[Any, Exception]] = []
        for factory in self._iter_widget_class(model):
            try:
                try:
                    widget = factory(self)
                except TypeError:
                    widget = factory()
                widget_id = get_widget_class_id(type(widget))
                reg = _actions.AppActionRegistry.instance()
                if self.model_app.name != "." and (
                    plugin_configs := self.app_profile.plugin_configs.get(widget_id)
                ):
                    params = {}
                    for k, v in plugin_configs.items():
                        params[k] = v["value"]
                    cfgs = reg._plugin_default_configs
                    cfg_type = cfgs[widget_id].config_class
                    # widget should always have `update_configs` in this case
                    widget.update_configs(cfg_type(**params))
                widget.update_model(model)
            except Exception as e:
                exceptions.append((factory, e))
            else:
                break
        else:
            raise ValueError(
                f"Failed to create a widget for {_short_repr(model)}. Errors:\n"
                f"{_format_exceptions(exceptions)}"
            ) from exceptions[-1][1]
        if exceptions:
            raise exceptions[-1][1]

        return widget

    def _on_command_execution(self, id: str, result: Future):
        if exc := result.exception():
            _LOGGER.exception("Command %r failed: %r", id, exc)
            return
        if action := self.model_app.registered_actions.get(id):
            if getattr(action.callback, NO_RECORDING_FIELD, False):
                return None
            self._history_command.add(id)

    def _process_update_inplace(
        self,
        contexts: list[ModelParameter | WindowParameter],
        model: WidgetDataModel,
    ):
        input_window = self._window_for_workflow_id(contexts[0].value)
        input_window.update_model(model)
        input_window._update_model_workflow(model.workflow)
        self.current_window = input_window


def _short_repr(obj: Any) -> str:
    obj_repr = repr(obj)
    if len(obj_repr) > 50:
        obj_repr = obj_repr[:50] + "..."
    return obj_repr


def _format_exceptions(exceptions: list[tuple[Any, Exception]]) -> str:
    strs: list[str] = []
    for factory, e in exceptions:
        fname = getattr(factory, "__himena_widget_id__", repr(factory))
        strs.append(f"- {type(e).__name__} in {fname}\n  {e}")
    return "\n".join(strs)


def _iter_sorted(matched: list[tuple[tuple[int, int], type]]) -> Iterator[type]:
    _s = sorted(matched, key=lambda x: x[0], reverse=True)
    yield from (cls for _, cls in _s)


def _tab_to_be_used(self: MainWindow) -> TabArea[_W]:
    if self._new_widget_behavior is NewWidgetBehavior.WINDOW:
        idx = self._backend_main_window._current_tab_index()
        if idx is None:
            self.add_tab()
            idx = len(self.tabs) - 1
        elif self.tabs[idx].is_single_window:
            # find the first non-single-window tab
            for i, tab_candidate in self.tabs.enumerate():
                if not tab_candidate.is_single_window:
                    tabarea = tab_candidate
                    idx = i
                    break
            else:
                tabarea = self.add_tab()
                idx = len(self.tabs) - 1
        tabarea = self.tabs[idx]
    else:
        tabarea = self.add_tab()
    return tabarea
