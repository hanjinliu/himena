from __future__ import annotations

from typing import Any, Generic, Hashable, TypeVar
from app_model import Application
from app_model.expressions import create_context
from psygnal import SignalGroup, Signal
from royalapp.types import (
    WidgetDataModel,
    ClipboardDataModel,
    NewWidgetBehavior,
    SubWindowState,
    DockArea,
    DockAreaString,
)
from royalapp._app_model._context import AppContext
from royalapp.widgets._backend import BackendMainWindow
from royalapp.widgets._tab_list import TabList, TabArea, SubWindow

_W = TypeVar("_W")  # backend widget type

_INITIALIZED_APPLICATIONS: dict[str, Application] = {}
_APP_INSTANCES: dict[str, list[MainWindow]] = {}


class MainWindowEvents(SignalGroup):
    window_activated = Signal()


class MainWindow(Generic[_W]):
    def __init__(self, backend: BackendMainWindow[_W], app: Application) -> None:
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

    @property
    def tabs(self) -> TabList[_W]:
        """Tab list object."""
        return self._tab_list

    @property
    def model_app(self) -> Application:
        """The app-model application instance."""
        return self._model_app

    def add_tab(self, title: str | None = None) -> TabArea[_W]:
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
        QSubWindow
            A sub-window widget. The added widget is available by calling
            `main_widget()` method.
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
        return out

    def add_dock_widget(
        self,
        widget: _W,
        *,
        title: str | None,
        area: DockAreaString | DockArea | None = DockArea.RIGHT,
        allowed_areas: list[DockAreaString | DockArea] | None = None,
    ):
        self._backend_main_window.add_dock_widget(
            widget, title=title, area=area, allowed_areas=allowed_areas
        )
        return None

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
            A sub-window with `data` as the internal data.
        """
        wd = WidgetDataModel(value=data, type=type, source=None, title=title)
        return self.add_data_model(wd)

    def add_data_model(self, model_data: WidgetDataModel) -> SubWindow[_W]:
        cls = self._backend_main_window._pick_widget_class(model_data.type)
        widget = cls.from_model(model_data)
        return self.add_widget(widget, title=model_data.title)

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


def current_instance(name: str) -> MainWindow[_W]:
    return _APP_INSTANCES[name][-1]


def set_current_instance(name: str, instance: MainWindow[_W]) -> None:
    if name not in _APP_INSTANCES:
        _APP_INSTANCES[name] = []
    elif instance in _APP_INSTANCES[name]:
        _APP_INSTANCES[name].remove(instance)
    _APP_INSTANCES[name].append(instance)
    return None


def remove_instance(name: str, instance: MainWindow[_W]) -> None:
    if name in _APP_INSTANCES:
        _APP_INSTANCES[name].remove(instance)
    return None


def _init_application(app: Application) -> None:
    from royalapp._app_model._actions import ACTIONS_AND_MENUS

    for each in ACTIONS_AND_MENUS:
        if isinstance(each, list):
            app.menus.append_menu_items([each[0]])
            app.register_actions(each[1:])
        else:
            app.register_action(each)

    app.injection_store.namespace = {
        "MainWindow": MainWindow,
        "TabArea": TabArea,
        "SubWindow": SubWindow,
        "WidgetDataModel": WidgetDataModel,
    }

    ### providers and processors
    @app.injection_store.mark_provider
    def _current_instance() -> MainWindow:
        return current_instance(app.name)

    @app.injection_store.mark_provider
    def _current_tab_area() -> TabArea:
        return current_instance(app.name).tabs.current()

    @app.injection_store.mark_provider
    def _current_window() -> SubWindow:
        ins = current_instance(app.name)
        if area := ins.tabs.current():
            return area.current()
        return None

    @app.injection_store.mark_provider
    def _provide_file_output() -> WidgetDataModel:
        return current_instance(app.name)._backend_main_window._provide_file_output()

    @app.injection_store.mark_processor
    def _process_file_input(file_data: WidgetDataModel) -> None:
        ins = current_instance(app.name)
        cls = ins._backend_main_window._pick_widget_class(file_data.type)
        widget = cls.from_model(file_data)
        ins.add_widget(widget, title=file_data.title)
        return None

    @app.injection_store.mark_provider
    def _get_clipboard_data() -> ClipboardDataModel:
        return current_instance(app.name)._backend_main_window._clipboard_data()

    @app.injection_store.mark_processor
    def _process_clipboard_data(clip_data: ClipboardDataModel) -> None:
        ins = current_instance(app.name)
        ins._backend_main_window._set_clipboard_data(clip_data)
        return None


def init_application(app: Application) -> Application:
    """Get application by name."""
    if app.name not in _INITIALIZED_APPLICATIONS:
        _init_application(app)
        _INITIALIZED_APPLICATIONS[app.name] = app
    return app
