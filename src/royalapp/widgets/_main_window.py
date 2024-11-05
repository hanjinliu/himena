from __future__ import annotations

from contextlib import contextmanager
import inspect
from pathlib import Path
from typing import Any, Generic, Hashable, TypeVar
from weakref import WeakSet
from app_model import Application
from app_model.expressions import create_context
from psygnal import SignalGroup, Signal
from royalapp.consts import MenuId
from royalapp.io import get_readers
from royalapp.types import (
    Parametric,
    WidgetDataModel,
    NewWidgetBehavior,
    DockArea,
    DockAreaString,
    BackendInstructions,
)
from royalapp._app_model._context import AppContext
from royalapp._descriptors import ProgramaticMethod, LocalReaderMethod
from royalapp.profile import list_recent_files, append_recent_files
from royalapp.widgets._backend import BackendMainWindow
from royalapp.widgets._open_recent import action_for_file
from royalapp.widgets._tab_list import TabList, TabArea
from royalapp.widgets._wrapper import SubWindow, DockWidget

_W = TypeVar("_W")  # backend widget type
_T = TypeVar("_T")  # internal data type


class MainWindowEvents(SignalGroup):
    window_activated = Signal()


class MainWindow(Generic[_W]):
    def __init__(self, backend: BackendMainWindow[_W], app: Application) -> None:
        from royalapp.widgets._initialize import set_current_instance

        self.events = MainWindowEvents()
        self._backend_main_window = backend
        self._tab_list = TabList(self._backend_main_window)
        self._new_widget_behavior = NewWidgetBehavior.WINDOW
        self._model_app = app
        self._instructions = BackendInstructions()
        set_current_instance(app, self)
        self._backend_main_window._connect_activation_signal(
            self.events.window_activated
        )
        self._ctx_keys = AppContext(create_context(self, max_depth=0))
        self._tab_list.changed.connect(self._backend_main_window._update_context)
        self.events.window_activated.connect(self._backend_main_window._update_context)
        self._dock_widgets = WeakSet[_W]()
        self._exec_confirmations = True
        self._open_recent_disposer = lambda: None
        self._update_open_recent_menu()

    @property
    def tabs(self) -> TabList[_W]:
        """Tab list object."""
        return self._tab_list

    @property
    def model_app(self) -> Application:
        """The app-model application instance."""
        return self._model_app

    @property
    def area_size(self) -> tuple[int, int]:
        """(width, height) of the main window tab area."""
        return self._backend_main_window._area_size()

    def add_tab(self, title: str | None = None) -> TabArea[_W]:
        """Add a new tab of given name."""
        n_tab = len(self.tabs)
        if title is None:
            title = f"Tab-{n_tab}"
        self._backend_main_window.add_tab(title)
        self._backend_main_window._set_current_tab_index(n_tab)
        return self.tabs[n_tab]

    @contextmanager
    def _animation_context(self, enabled: bool):
        old = self._instructions
        self._instructions = self._instructions.updated(animate=enabled)
        try:
            yield None
        finally:
            self._instructions = old

    def widget_for_id(self, identifier: int) -> SubWindow[_W] | None:
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
        self._backend_main_window.add_dock_widget(
            widget, title=title, area=area, allowed_areas=allowed_areas
        )
        dock = DockWidget(widget, self._backend_main_window, identifier=_identifier)
        self._dock_widgets.add(dock.widget)
        return dock

    def add_dialog(self, widget: _W, *, title: str | None = None):
        return self._backend_main_window.add_dialog_widget(widget, title=title)

    def add_data(
        self,
        data: Any,
        type: Hashable | None = None,
        title: str | None = None,
    ) -> SubWindow[_W]:
        """
        Add any data as a widget data model.

        Parameters
        ----------
        data : Any
            Any object.
        type : Hashable, optional
            Any hashable object that describes the type of the data. If not given,
            the Python type of the data will be used. This type must be registered with
            a proper backend widget class.
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
        cls = self._backend_main_window._pick_widget_class(model_data.type)
        widget = cls.from_model(model_data)
        sub_win = self.add_widget(widget, title=model_data.title)
        if isinstance(method := model_data.method, LocalReaderMethod):
            sub_win.update_default_save_path(method.path)
        return sub_win

    def add_parametric_element(
        self,
        fn: Parametric[_T],
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
        if title is None:
            title = getattr(fn, "__name__", "Run ...")
        sig = inspect.signature(fn)
        back_main = self._backend_main_window
        back_param_widget, connection = back_main._parametric_widget(sig)
        param_widget = self.add_widget(back_param_widget, title=title)

        @connection
        def _callback(**kwargs):
            model = fn(**kwargs)
            cls = back_main._pick_widget_class(model.type)
            widget = cls.from_model(model)
            rect = param_widget.window_rect
            i_tab, i_win = param_widget._find_me(self)
            del self.tabs[i_tab][i_win]
            result_widget = self.tabs[i_tab].add_widget(
                widget, title=model.title, autosize=False
            )
            if size_hint := result_widget.size_hint():
                new_rect = (rect.left, rect.top, size_hint[0], size_hint[1])
            else:
                new_rect = rect
            result_widget.window_rect = new_rect
            return None

        return param_widget

    def read_file(self, file_path) -> SubWindow[_W]:
        """Read local file(s) and open as a new sub-window."""
        if hasattr(file_path, "__iter__") and not isinstance(file_path, (str, Path)):
            fp = [Path(f) for f in file_path]
        else:
            fp = Path(file_path)
        readers = get_readers(fp)
        model = readers[0](fp).with_source(fp)
        out = self.add_data_model(model)
        append_recent_files([file_path])
        self._update_open_recent_menu()
        return out

    def exec_action(self, id: str) -> None:
        """Execute an action by its ID."""
        self._model_app.commands.execute_command(id)
        return None

    def exec_confirmation_dialog(self, msg: str) -> bool:
        """Execute a confirmation dialog (True if Yes is selected)."""
        if not self._exec_confirmations:
            return True
        return self._backend_main_window._open_confirmation_dialog(msg)

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

    def _provide_file_output(self) -> tuple[WidgetDataModel, SubWindow[_W]]:
        if sub := self.current_window:
            model = sub.to_model()
            return model, sub
        else:
            raise ValueError("No active window.")

    def _update_open_recent_menu(self):
        file_paths = list_recent_files()[::-1]
        if len(file_paths) == 0:
            return None
        actions = [
            action_for_file(path, in_menu=i < 8) for i, path in enumerate(file_paths)
        ]
        self._open_recent_disposer()
        self._open_recent_disposer = self.model_app.register_actions(actions)
        self.model_app.menus.menus_changed.emit({MenuId.FILE_RECENT})
        return None
