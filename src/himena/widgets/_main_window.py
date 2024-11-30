from __future__ import annotations

from concurrent.futures import Future
from logging import getLogger
from pathlib import Path
from typing import (
    Any,
    Callable,
    Generic,
    Iterator,
    Literal,
    TypeVar,
    overload,
    TYPE_CHECKING,
)
from app_model.expressions import create_context
from psygnal import SignalGroup, Signal

from himena._app_model import AppContext, HimenaApplication
from himena._descriptors import ProgramaticMethod
from himena._open_recent import RecentFileManager, RecentSessionManager
from himena._utils import import_object
from himena.consts import NO_RECORDING_FIELD
from himena.plugins import _checker
from himena.profile import AppProfile, load_app_profile
from himena.style import Theme
from himena.types import (
    ClipboardDataModel,
    WidgetDataModel,
    NewWidgetBehavior,
    DockArea,
    DockAreaString,
    BackendInstructions,
)
from himena.session import from_yaml
from himena.widgets._backend import BackendMainWindow
from himena.widgets._hist import HistoryContainer, FileDialogHistoryDict
from himena.widgets._initialize import remove_instance
from himena.widgets._widget_list import TabList, TabArea, DockWidgetList
from himena.widgets._wrapper import ParametricWindow, SubWindow, DockWidget

if TYPE_CHECKING:
    from himena.widgets._widget_list import PathOrPaths

_W = TypeVar("_W")  # backend widget type
_T = TypeVar("_T")  # internal data type
_LOGGER = getLogger(__name__)


class MainWindowEvents(SignalGroup, Generic[_W]):
    """Main window events."""

    tab_activated = Signal(TabArea[_W])
    window_activated = Signal(SubWindow[_W])


class MainWindow(Generic[_W]):
    """The main window object."""

    def __init__(
        self,
        backend: BackendMainWindow[_W],
        app: HimenaApplication,  # must be initialized
        theme: Theme,
    ) -> None:
        from himena.widgets._initialize import set_current_instance

        self.events: MainWindowEvents[_W] = MainWindowEvents()
        self._backend_main_window = backend
        self._tab_list = TabList(backend)
        self._new_widget_behavior = NewWidgetBehavior.WINDOW
        self._model_app = app
        self._instructions = BackendInstructions()
        self._history_tab = HistoryContainer[int](max_size=20)
        self._history_command = HistoryContainer[str](max_size=200)
        self._history_closed = HistoryContainer[tuple[Path, str | None]](max_size=10)
        self._file_dialog_hist = FileDialogHistoryDict()
        set_current_instance(app.name, self)
        app.commands.executed.connect(self._on_command_execution)
        backend._connect_activation_signal(
            self._tab_activated,
            self._window_activated,
        )
        self._ctx_keys = AppContext(create_context(self, max_depth=0))
        self._tab_list.changed.connect(backend._update_context)
        self._dock_widget_list = DockWidgetList(backend)
        self._recent_manager = RecentFileManager.default(app)
        self._recent_manager.update_menu()
        self._recent_session_manager = RecentSessionManager.default(app)
        self._recent_session_manager.update_menu()
        self.theme = theme

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

        # update icon colors

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

    @property
    def tabs(self) -> TabList[_W]:
        """Tab list object."""
        return self._tab_list

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
    def clipboard(self) -> ClipboardDataModel | None:
        """Get the clipboard data as a ClipboardDataModel instance."""
        return self._backend_main_window._clipboard_data()

    @clipboard.setter
    def clipboard(self, data: str | ClipboardDataModel) -> None:
        """Set the clipboard data."""
        if isinstance(data, str):
            data = ClipboardDataModel(text=data)
        elif not isinstance(data, ClipboardDataModel):
            raise ValueError("Clipboard data must be a ClipboardDataModel instance.")
        _LOGGER.info("Setting clipboard data: %r", data)
        self._backend_main_window._set_clipboard_data(data)
        return None

    def add_tab(self, title: str | None = None) -> TabArea[_W]:
        """Add a new tab of given name."""
        n_tab = len(self.tabs)
        if title is None:
            title = f"Tab-{n_tab}"
        self._backend_main_window.add_tab(title)
        self.tabs.changed.emit()
        self._backend_main_window._set_current_tab_index(n_tab)
        return self.tabs[n_tab]

    def window_for_id(self, identifier: int) -> SubWindow[_W] | None:
        """Retrieve a sub-window by its identifier."""
        for win in self.iter_windows():
            if win._identifier == identifier:
                return win
        return None

    def _current_or_new_tab(self) -> tuple[int, TabArea[_W]]:
        if self._new_widget_behavior is NewWidgetBehavior.WINDOW:
            if len(self.tabs) == 0:
                self.add_tab()
                idx = 0
            else:
                idx = self._backend_main_window._current_tab_index()
            tabarea = self.tabs[idx]
        else:
            tabarea = self.add_tab()
            idx = len(self.tabs) - 1
        return idx, tabarea

    def add_widget(
        self,
        widget: _W,
        *,
        title: str | None = None,
    ) -> SubWindow[_W]:
        """
        Add a widget to the sub window.

        Parameters
        ----------
        widget : QtW.QWidget
            Widget to add.
        title : str, optional
            Title of the sub-window. If not given, its name will be automatically
            generated.

        Returns
        -------
        SubWindow
            The sub-window handler.
        """
        _, tabarea = self._current_or_new_tab()
        return tabarea.add_widget(widget, title=title)

    def add_dock_widget(
        self,
        widget: _W,
        *,
        title: str | None = None,
        area: DockAreaString | DockArea | None = DockArea.RIGHT,
        allowed_areas: list[DockAreaString | DockArea] | None = None,
        _identifier: int | None = None,
    ) -> DockWidget[_W]:
        """
        Add a custom widget as a dock widget of the main window.

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
        self._backend_main_window.add_dock_widget(
            widget, title=title, area=area, allowed_areas=allowed_areas
        )
        self._dock_widget_list._add_dock_widget(dock)
        return dock

    def add_data(
        self,
        data: Any,
        *,
        type: str | None = None,
        title: str | None = None,
    ) -> SubWindow[_W]:
        """
        Add any data as a widget data model.

        Parameters
        ----------
        data : Any
            Any object.
        type : str, optional
            Any str that describes the type of the data. If not given, the Python type
            of the data will be used. This type must be registered with a proper backend
            widget class.
        title : str, optional
            Title of the sub-window.

        Returns
        -------
        SubWindow
            The sub-window handler.
        """
        wd = WidgetDataModel(
            value=data, type=type, title=title, method=ProgramaticMethod()
        )
        return self.add_data_model(wd)

    def add_data_model(self, model_data: WidgetDataModel) -> SubWindow[_W]:
        """Add a widget data model as a widget."""
        _, tabarea = self._current_or_new_tab()
        return tabarea.add_data_model(model_data)

    def add_function(
        self,
        func: Callable[..., _T],
        *,
        preview: bool = False,
        title: str | None = None,
        show_parameter_labels: bool = True,
        auto_close: bool = True,
    ) -> ParametricWindow[_W]:
        """
        Add a function as a parametric sub-window.

        The input function must return a `WidgetDataModel` instance, which can be
        interpreted by the application.

        Parameters
        ----------
        fn : function (...) -> WidgetDataModel
            Function that generates a model from the input parameters.
        title : str, optional
            Title of the sub-window.

        Returns
        -------
        SubWindow
            The sub-window instance that represents the output model.
        """
        _, tabarea = self._current_or_new_tab()
        return tabarea.add_function(
            func, title=title, preview=preview,
            show_parameter_labels=show_parameter_labels, auto_close=auto_close,
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
    ) -> ParametricWindow[_W]:
        _, area = self._current_or_new_tab()
        return area.add_parametric_widget(
            widget,
            callback,
            title=title,
            preview=preview,
            auto_close=auto_close,
            auto_size=auto_size,
        )

    def read_file(
        self,
        file_path: PathOrPaths,
        plugin: str | None = None,
    ) -> SubWindow[_W]:
        """Read local file(s) and open as a new sub-window."""
        _, tabarea = self._current_or_new_tab()
        return tabarea.read_file(file_path, plugin=plugin)

    def read_files(self, file_paths: PathOrPaths):
        """Read multiple files and open as new sub-windows in a same tab."""
        _, tabarea = self._current_or_new_tab()
        return tabarea.read_files(file_paths)

    def read_session(self, path: str | Path) -> None:
        """Read a session file and open the session."""
        fp = Path(path)
        from_yaml(fp).update_gui(self)
        # always plugin=None for reading a session file as a session
        self._recent_session_manager.append_recent_files([(fp, None)])
        self.set_status_tip(f"Session loaded: {fp}", duration=5)
        return None

    def save_session(self, path: str | Path) -> None:
        """Save the current session to a file."""
        from himena.session import AppSession

        path = Path(path)
        AppSession.from_gui(self).dump_yaml(path)
        self.set_status_tip(f"Session saved to {path}")
        self._recent_session_manager.append_recent_files([(path, None)])
        return None

    def clear(self) -> None:
        """Clear all widgets in the main window."""
        self.tabs.clear()
        self.dock_widgets.clear()
        return None

    def set_status_tip(self, text: str, duration: float = 10.0) -> None:
        """Set the status tip of the main window."""
        self._backend_main_window._set_status_tip(text, duration)
        return None

    def exec_action(self, id: str, with_params: dict[str, Any] | None = None) -> None:
        """Execute an action by its ID."""
        self._model_app.commands.execute_command(id).result()
        if with_params is not None:
            if tab := self.tabs.current():
                param_widget = tab[-1]
                if not isinstance(param_widget, ParametricWindow):
                    raise ValueError(
                        f"Parametric widget expected but got {param_widget}."
                    )
                param_widget._callback_with_params(with_params)
            else:  # pragma: no cover
                raise RuntimeError("Unreachable code.")
        return None

    def exec_confirmation_dialog(self, msg: str) -> bool:
        """Execute a confirmation dialog (True if Yes is selected)."""
        if not self._instructions.confirm:
            return True
        return self._backend_main_window._request_choice_dialog(
            title="Confirmation",
            message=msg,
            choices=[("Yes", True), ("No", False)],
        )

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
        return None

    def close(self) -> None:
        """Close the main window."""
        self._backend_main_window._exit_main_window(confirm=False)
        remove_instance(self.model_app.name, self)
        return None

    @property
    def current_window(self) -> SubWindow[_W] | None:
        """Get the current sub-window."""
        idx_tab = self._backend_main_window._current_tab_index()
        if idx_tab is None:
            return None
        idx_win = self._backend_main_window._current_sub_window_index()
        if idx_win is None:
            return None
        return self.tabs[idx_tab][idx_win]

    @current_window.setter
    def current_window(self, win: SubWindow[_W] | None) -> None:
        """Set the current sub-window."""
        if win is None:
            self._backend_main_window._set_current_tab_index(None)
            self._backend_main_window._set_current_sub_window_index(None)
            return None
        for i_tab, tab in self.tabs.enumerate():
            for i_win, sub in tab.enumerate():
                if sub is win:
                    self._backend_main_window._set_current_tab_index(i_tab)
                    self._backend_main_window._set_current_sub_window_index(i_win)
                    return None
        return None

    def iter_windows(self) -> Iterator[SubWindow[_W]]:
        """Iterate over all the sub-windows in this main window."""
        for tab in self.tabs:
            yield from tab

    def _provide_file_output(self) -> tuple[WidgetDataModel, SubWindow[_W]]:
        if sub := self.current_window:
            model = sub.to_model()
            return model, sub
        else:
            raise ValueError("No active window.")

    def _tab_activated(self, i: int):
        self.events.tab_activated.emit(self.tabs[i])
        self._history_tab.add(i)
        return None

    def move_window(self, sub: SubWindow[_W], target_index: int) -> None:
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
        win = self.tabs[i_tab]._pop_no_emit(i_win)
        old_rect = win.rect
        if target_index < 0:
            self.add_tab()
        self.tabs[target_index].append(win, title)
        win.rect = old_rect
        self.tabs.current_index = i_tab
        return None

    def _window_activated(self):
        back = self._backend_main_window
        back._update_context()
        i_tab = back._current_tab_index()
        if i_tab is None:
            return back._update_control_widget(None)
        tab = self.tabs[i_tab]
        if len(tab) == 0:
            return back._update_control_widget(None)
        i_win = back._current_sub_window_index()
        if i_win is None or len(tab) <= i_win:
            return back._update_control_widget(None)
        _LOGGER.debug("Window activated: %r-th window in %r-th tab", i_win, i_tab)
        win = tab[i_win]
        back._update_control_widget(win.widget)
        _checker.call_window_activated_callback(win.widget)
        self.events.window_activated.emit(win)
        return None

    def _pick_widget_class(self, model: WidgetDataModel) -> type[_W]:
        """Pick the most suitable widget class for the given model."""
        if model.force_open_with:
            return import_object(model.force_open_with)
        widget_classes, fallback_class = self._backend_main_window._list_widget_class(
            model.type
        )
        if not widget_classes:
            return fallback_class
        complete_match = [
            (priority, cls)
            for cls_type, cls, priority in widget_classes
            if cls_type == model.type
        ]
        if complete_match:
            return max(complete_match, key=lambda x: x[0])[1]
        subtype_match = [
            ((cls_type.count("."), priority), cls)
            for cls_type, cls, priority in widget_classes
        ]
        return max(subtype_match, key=lambda x: x[0])[1]

    def _on_command_execution(self, id: str, result: Future):
        if exc := result.exception():
            _LOGGER.exception("Command %r failed: %r", id, exc)
            return
        if action := self.model_app._registered_actions.get(id):
            if getattr(action.callback, NO_RECORDING_FIELD, False):
                return None
            self._history_command.add(id)
