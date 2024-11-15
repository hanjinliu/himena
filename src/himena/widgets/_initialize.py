from __future__ import annotations

from typing import TypeVar
from logging import getLogger
from app_model import Application
from himena.types import (
    Parametric,
    WidgetDataModel,
    ClipboardDataModel,
    ParametricWidgetTuple,
)
from himena.widgets._main_window import MainWindow
from himena.widgets._widget_list import TabArea
from himena.widgets._wrapper import SubWindow

_W = TypeVar("_W")  # backend widget type

_APP_INSTANCES: dict[str, list[MainWindow]] = {}
_LOGGER = getLogger(__name__)


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
        instances = _APP_INSTANCES[name]
        if instance in instances:
            instances.remove(instance)
    return None


def init_application(app: Application) -> Application:
    from himena._app_model.actions import ACTIONS, SUBMENUS

    app.register_actions(ACTIONS)
    app.menus.append_menu_items(SUBMENUS)

    app.injection_store.namespace = {
        "MainWindow": MainWindow,
        "TabArea": TabArea,
        "SubWindow": SubWindow,
        "WidgetDataModel": WidgetDataModel,
    }

    ### providers and processors
    @app.injection_store.mark_provider
    def _current_instance() -> MainWindow:
        _LOGGER.debug("providing for %r", MainWindow.__name__)
        return current_instance(app.name)

    @app.injection_store.mark_provider
    def _current_tab_area() -> TabArea:
        _LOGGER.debug("providing for %r", TabArea.__name__)
        return current_instance(app.name).tabs.current()

    @app.injection_store.mark_provider
    def _current_window() -> SubWindow:
        _LOGGER.debug("providing for %r", SubWindow.__name__)
        ins = current_instance(app.name)
        if area := ins.tabs.current():
            return area.current()
        return None

    @app.injection_store.mark_provider
    def _provide_data_model() -> WidgetDataModel:
        _LOGGER.debug("providing for %r", WidgetDataModel.__name__)
        return current_instance(app.name)._provide_file_output()[0]

    @app.injection_store.mark_processor
    def _process_file_input(file_data: WidgetDataModel) -> None:
        _LOGGER.debug("processing %r", file_data)
        ins = current_instance(app.name)
        ins.add_data_model(file_data)
        return None

    @app.injection_store.mark_processor
    def _process_file_inputs(file_data: list[WidgetDataModel]) -> None:
        _LOGGER.debug("processing %r", file_data)
        for each in file_data:
            _process_file_input(each)

    @app.injection_store.mark_provider
    def _get_clipboard_data() -> ClipboardDataModel:
        _LOGGER.debug("providing for %r", ClipboardDataModel.__name__)
        return current_instance(app.name).clipboard

    @app.injection_store.mark_processor
    def _process_clipboard_data(clip_data: ClipboardDataModel) -> None:
        if clip_data is None:
            return None
        _LOGGER.debug("processing %r", clip_data)
        # set data to clipboard
        ins = current_instance(app.name)
        ins.clipboard = clip_data
        return None

    @app.injection_store.mark_processor
    def _process_parametric(fn: Parametric) -> None:
        if fn is None:
            return None
        _LOGGER.debug("processing %r", fn)
        ins = current_instance(app.name)
        ins.add_function(fn, preview=fn.preview)
        return None

    @app.injection_store.mark_processor
    def _process_parametric_widget(tup: ParametricWidgetTuple) -> None:
        if tup is None:
            return None
        tup = ParametricWidgetTuple(*tup)
        _LOGGER.debug("processing %r", tup)
        ins = current_instance(app.name)
        ins.add_parametric_widget(tup.widget, tup.callback, title=tup.title)

    return app
