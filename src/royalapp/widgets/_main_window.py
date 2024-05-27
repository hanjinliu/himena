from __future__ import annotations

from typing import Any, Generic, Hashable, TypeVar
from app_model import Application
from royalapp.types import (
    TabTitle,
    WindowTitle,
    WidgetDataModel,
    NewWidgetBehavior,
    SubWindowState,
)

from royalapp.widgets._backend import BackendMainWindow
from royalapp.widgets._tab_list import TabList, TabArea, WidgetWrapper

_W = TypeVar("_W")  # backend widget type

_APPLICATIONS: dict[str, Application] = {}
_APP_INSTANCES: dict[str, list[MainWindow]] = {}


def get_application(name: str) -> Application:
    """Get application by name."""
    if name not in _APPLICATIONS:
        app = Application(name)
        _APPLICATIONS[name] = app
        _init_application(app)
    return _APPLICATIONS[name]


class MainWindow(Generic[_W]):
    def __init__(self, backend: BackendMainWindow[_W], app: Application) -> None:
        self._backend_main_window = backend
        self._tab_list = TabList(self._backend_main_window)
        self._new_widget_behavior = NewWidgetBehavior.WINDOW
        self._model_app = app
        set_current_instance(app, self)

    @property
    def tabs(self) -> TabList[_W]:
        return self._tab_list

    @property
    def model_app(self) -> Application:
        """The app-model application instance."""
        return self._model_app

    def add_tab(self, title: TabTitle | None) -> TabArea[_W]:
        return self._backend_main_window.add_tab(title)

    def add_widget(
        self,
        widget: _W,
        *,
        title: str | None = None,
    ) -> WidgetWrapper[_W]:
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
        self._backend_main_window._set_current_tab_index(idx)
        if self._new_widget_behavior is NewWidgetBehavior.TAB:
            nwindows = len(tabarea)
            self._backend_main_window._set_window_state(
                idx, nwindows - 1, SubWindowState.FULL
            )
        return out

    def add_data(
        self,
        data: Any,
        type: Hashable,
        title: str | None = None,
    ) -> WidgetWrapper[_W]:
        fd = WidgetDataModel(value=data, file_type=type, source=None)
        return self.add_data_model(fd)

    def add_data_model(self, model_data: WidgetDataModel) -> WidgetWrapper[_W]:
        cls = self._backend_main_window._pick_widget_class(model_data.type)
        widget = cls.import_data(model_data)
        return self.add_widget(widget)

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
    from royalapp._app_model._actions import ACTIONS

    app.register_actions(ACTIONS)

    @app.injection_store.mark_provider
    def _current_instance() -> MainWindow:
        return current_instance(app.name)

    @app.injection_store.mark_provider
    def _current_tab_name() -> TabTitle:
        ins = current_instance(app.name)
        idx = ins._backend_main_window._current_tab_index()
        return ins._backend_main_window._get_tab_name_list()[idx]

    @app.injection_store.mark_provider
    def _current_sub_window_title() -> WindowTitle:
        ins = current_instance(app.name)
        wrapper = ins.tabs.current().current()
        return ins._backend_main_window._window_title(wrapper.widget)

    @app.injection_store.mark_provider
    def _provide_file_output() -> WidgetDataModel:
        return current_instance(app.name)._backend_main_window._provide_file_output()

    @app.injection_store.mark_processor
    def _process_file_input(file_data: WidgetDataModel) -> None:
        ins = current_instance(app.name)
        cls = ins._backend_main_window._pick_widget_class(file_data.type)
        widget = cls.import_data(file_data)
        ins.add_widget(widget, title=file_data.title)
        return None
