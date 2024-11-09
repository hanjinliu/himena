from __future__ import annotations

from logging import getLogger
from pathlib import Path
from typing import Any, Callable, Generic, Iterator, Literal, TypeVar, overload
from app_model import Application
from app_model.expressions import create_context
from psygnal import SignalGroup, Signal

from himena._app_model._context import AppContext
from himena._descriptors import ProgramaticMethod
from himena._open_recent import RecentFileManager, RecentSessionManager
from himena.types import (
    ClipboardDataModel,
    Parametric,
    WidgetDataModel,
    NewWidgetBehavior,
    DockArea,
    DockAreaString,
    BackendInstructions,
)
from himena.session import from_yaml
from himena.widgets._backend import BackendMainWindow
from himena.widgets._hist import ActivationHistory
from himena.widgets._widget_list import TabList, TabArea, DockWidgetList
from himena.widgets._wrapper import SubWindow, DockWidget

_W = TypeVar("_W")  # backend widget type
_T = TypeVar("_T")  # internal data type
_LOGGER = getLogger(__name__)


class MainWindowEvents(SignalGroup, Generic[_W]):
    """Main window events."""

    tab_activated = Signal(TabArea[_W])
    window_activated = Signal(SubWindow[_W])


class MainWindow(Generic[_W]):
    """The main window object."""

    def __init__(self, backend: BackendMainWindow[_W], app: Application) -> None:
        from himena.widgets._initialize import set_current_instance

        self.events: MainWindowEvents[_W] = MainWindowEvents()
        self._backend_main_window = backend
        self._tab_list = TabList(backend)
        self._new_widget_behavior = NewWidgetBehavior.WINDOW
        self._model_app = app
        self._instructions = BackendInstructions()
        self._history_tab = ActivationHistory[int]()
        set_current_instance(app.name, self)
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

    @property
    def tabs(self) -> TabList[_W]:
        """Tab list object."""
        return self._tab_list

    @property
    def dock_widgets(self) -> DockWidgetList[_W]:
        """Dock widget list object."""
        return self._dock_widget_list

    @property
    def model_app(self) -> Application:
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
    def clipboard(self, data: ClipboardDataModel) -> None:
        """Set the clipboard data."""
        if not isinstance(data, ClipboardDataModel):
            raise ValueError("Clipboard data must be a ClipboardDataModel instance.")
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
        """Retrieve a widget by its identifier."""
        for tab in self.tabs:
            for widget in tab:
                if widget._identifier == identifier:
                    return widget
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

    def exec_dialog(self, widget: _W, *, title: str | None = None):
        return self._backend_main_window.add_dialog_widget(widget, title=title)

    def add_data(
        self,
        data: Any,
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

    def add_parametric_element(
        self,
        func: Callable[..., _T],
        *,
        title: str | None = None,
    ) -> SubWindow[_W]:
        """
        Add a sub-window that generates a model from a function.

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
        fn = Parametric(func)
        if title is None:
            title = fn.name
        sig = fn.get_signature()
        back_main = self._backend_main_window
        back_param_widget, connection = back_main._parametric_widget(sig)
        param_widget = self.add_widget(back_param_widget, title=title)

        connection(fn.make_connection(self, param_widget))
        return param_widget

    def read_file(self, file_path: str | Path | list[str | Path]) -> SubWindow[_W]:
        """Read local file(s) and open as a new sub-window."""
        _, tabarea = self._current_or_new_tab()
        return tabarea.read_file(file_path)

    def read_session(self, path: str | Path) -> None:
        """Read a session file and open the session."""
        fp = Path(path)
        session = from_yaml(fp)
        session.to_gui(self)
        self._recent_session_manager.append_recent_files([fp])
        self._recent_session_manager.update_menu()
        return None

    def save_session(self, path: str | Path) -> None:
        """Save the current session to a file."""
        from himena.session import AppSession

        session = AppSession.from_gui(self)
        session.dump_yaml(path)
        return None

    def clear(self) -> None:
        """Clear all widgets in the main window."""
        self.tabs.clear()
        return None

    def exec_action(self, id: str, **kwargs) -> None:
        """Execute an action by its ID."""
        result = self._model_app.commands.execute_command(id).result()
        if kwargs and isinstance(result, Parametric) and (tab := self.tabs.current()):
            param_widget = tab[-1]
            result.make_connection(self, param_widget)(**kwargs)
        return None

    def exec_confirmation_dialog(self, msg: str) -> bool:
        """Execute a confirmation dialog (True if Yes is selected)."""
        if not self._instructions.confirm:
            return True
        return self._backend_main_window._open_confirmation_dialog(msg)

    @overload
    def exec_file_dialog(
        self,
        mode: Literal["r", "d", "w"] = "r",
        extension_default: str | None = None,
        allowed_extensions: list[str] | None = None,
    ) -> Path | None: ...
    @overload
    def exec_file_dialog(
        self,
        mode: Literal["rm"],
        extension_default: str | None = None,
        allowed_extensions: list[str] | None = None,
    ) -> list[Path] | None: ...

    def exec_file_dialog(self, mode, extension_default=None, allowed_extensions=None):
        if res := self._instructions.file_dialog_response:
            return res()
        return self._backend_main_window._open_file_dialog(
            mode,
            extension_default=extension_default,
            allowed_extensions=allowed_extensions,
        )

    def show(self, run: bool = False) -> None:
        """
        Show the main window.

        Parameters
        ----------
        run : bool, default False
            If True, run the application event loop.
        """
        self._backend_main_window.show()
        if run:
            self._backend_main_window._run_app()
        return None

    def close(self) -> None:
        """Close the main window."""
        self._backend_main_window._exit_main_window()
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
        for _i_tab, tab in enumerate(self.tabs):
            for _i_win, win in enumerate(tab):
                if win is sub:
                    i_tab = _i_tab
                    i_win = _i_win
                    break

        if i_tab is None or i_win is None or target_index == i_tab:
            return None
        title = self.tabs[i_tab][i_win].title
        win = self.tabs[i_tab].pop(i_win)
        old_rect = win.rect
        if target_index < 0:
            self.add_tab()
        self.tabs[target_index].append(win, title)
        win.rect = old_rect
        self.tabs.current_index = i_tab

    def _window_activated(self):
        back = self._backend_main_window
        back._update_context()
        i_tab = back._current_tab_index()
        if i_tab is None:
            return None
        tab = self.tabs[i_tab]
        if len(tab) == 0:
            return None
        i_win = back._current_sub_window_index()
        if i_win is None:
            return None
        if len(tab) <= i_win:
            return None
        _LOGGER.info("Window activated: %r-th window in %r-th tab", i_win, i_tab)
        self.events.window_activated.emit(tab[i_win])
        return None
