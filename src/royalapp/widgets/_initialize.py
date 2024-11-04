from __future__ import annotations

from typing import TypeVar
from app_model import Application
from royalapp.types import WidgetDataModel, ClipboardDataModel
from royalapp.widgets._main_window import MainWindow
from royalapp.widgets._tab_list import TabArea
from royalapp.widgets._wrapper import SubWindow

_W = TypeVar("_W")  # backend widget type

_INITIALIZED_APPLICATIONS: dict[str, Application] = {}
_APP_INSTANCES: dict[str, list[MainWindow]] = {}


def current_instance(name: str) -> MainWindow[_W]:
    """Get current instance of the main window (raise if not exists)."""
    return _APP_INSTANCES[name][-1]


def set_current_instance(name: str, instance: MainWindow[_W]) -> None:
    """Set the instance as the current one."""
    if name not in _APP_INSTANCES:
        _APP_INSTANCES[name] = []
    elif instance in _APP_INSTANCES[name]:
        _APP_INSTANCES[name].remove(instance)
    _APP_INSTANCES[name].append(instance)
    return None


def remove_instance(name: str, instance: MainWindow[_W]) -> None:
    """Remove the instance from the list."""
    if name in _APP_INSTANCES:
        _APP_INSTANCES[name].remove(instance)
    return None


def _init_application(app: Application) -> None:
    from royalapp._app_model.actions import (
        tab_actions,
        window_actions,
        tools_actions,
        file_actions,
    )

    app.register_actions(file_actions.ACTIONS)
    app.register_actions(tab_actions.ACTIONS)
    app.register_actions(tools_actions.ACTIONS)
    app.register_actions(window_actions.ACTIONS)
    app.menus.append_menu_items(file_actions.SUBMENUS)
    app.menus.append_menu_items(window_actions.SUBMENUS)

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
    def _provide_data_model() -> WidgetDataModel:
        return current_instance(app.name)._provide_file_output()[0]

    @app.injection_store.mark_processor
    def _process_file_input(file_data: WidgetDataModel) -> None:
        ins = current_instance(app.name)
        sub_win = ins.add_data_model(file_data)
        if (method := file_data.method) is not None:
            sub_win._update_widget_data_model_method(method)
        return None

    @app.injection_store.mark_processor
    def _process_file_inputs(file_data: list[WidgetDataModel]) -> None:
        for each in file_data:
            _process_file_input(each)

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