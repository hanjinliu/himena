from __future__ import annotations

from pathlib import Path
from typing import Any, Generic, Hashable, TypeVar
from weakref import WeakSet
from app_model import Application
from app_model.expressions import create_context
from psygnal import SignalGroup, Signal
from royalapp.consts import MenuId
from royalapp.io import get_readers
from royalapp.types import (
    WidgetDataModel,
    NewWidgetBehavior,
    SubWindowState,
    DockArea,
    DockAreaString,
)
from royalapp._app_model._context import AppContext
from royalapp._descriptors import ProgramaticMethod, LocalReaderMethod
from royalapp.profile import list_recent_files, append_recent_files
from royalapp.widgets._backend import BackendMainWindow
from royalapp.widgets._open_recent import action_for_file
from royalapp.widgets._tab_list import TabList, TabArea
from royalapp.widgets._wrapper import SubWindow, DockWidget

_W = TypeVar("_W")  # backend widget type


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
        self._backend_main_window.add_tab(title)
        idx = len(self.tabs) - 1
        self._backend_main_window._set_current_tab_index(idx)
        return self.tabs[idx]

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
        if self._new_widget_behavior is NewWidgetBehavior.WINDOW:
            if len(self.tabs) == 0:
                self.add_tab("Tab")
                idx = 0
            else:
                idx = self._backend_main_window._current_tab_index()
            tabarea = self.tabs[idx]
        else:
            tabarea = self.add_tab(title)
            idx = len(self.tabs) - 1
        out = tabarea.add_widget(widget, title=title)

        # connect events
        out.state_changed.connect(self._backend_main_window._update_context)

        self._backend_main_window._set_current_tab_index(idx)
        if self._new_widget_behavior is NewWidgetBehavior.TAB:
            nwindows = len(tabarea)
            self._backend_main_window._set_window_state(
                idx, nwindows - 1, SubWindowState.FULL
            )
        else:
            self._backend_main_window._set_current_sub_window_index(len(tabarea) - 1)
        return out

    def add_dock_widget(
        self,
        widget: _W,
        *,
        title: str | None = None,
        area: DockAreaString | DockArea | None = DockArea.RIGHT,
        allowed_areas: list[DockAreaString | DockArea] | None = None,
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
        dock = DockWidget(widget, self._backend_main_window)
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
