from __future__ import annotations

from pathlib import Path
from typing import TypeVar, TYPE_CHECKING
from logging import getLogger
import weakref
from app_model import Application
from himena.types import (
    Parametric,
    WidgetDataModel,
    ClipboardDataModel,
    ParametricWidgetTuple,
)
from himena.widgets._widget_list import TabArea
from himena.widgets._wrapper import SubWindow

if TYPE_CHECKING:
    from himena.widgets._main_window import MainWindow

_W = TypeVar("_W")  # backend widget type

_APP_INSTANCES: dict[str, list[MainWindow]] = {}
_LOGGER = getLogger(__name__)


def current_instance(name: str | None = None) -> MainWindow[_W]:
    """Get current instance of the main window (raise if not exists)."""
    if name is None:
        name = next(iter(_APP_INSTANCES))
    return _APP_INSTANCES[name][-1]


def set_current_instance(name: str, instance: MainWindow[_W]) -> None:
    """Set the instance as the current one."""
    if name not in _APP_INSTANCES:
        _APP_INSTANCES[name] = []
    elif instance in _APP_INSTANCES[name]:
        _APP_INSTANCES[name].remove(instance)
    _APP_INSTANCES[name].append(instance)
    return None


def cleanup():
    """Close all instances and clear the list."""
    for instances in _APP_INSTANCES.copy().values():
        for instance in instances:
            instance.close()
    _APP_INSTANCES.clear()


def remove_instance(name: str, instance: MainWindow[_W]) -> None:
    """Remove the instance from the list."""
    if name in _APP_INSTANCES:
        instances = _APP_INSTANCES[name]
        if instance in instances:
            instances.remove(instance)
            instance.model_app.destroy(instance.model_app.name)
        if not instances:
            _APP_INSTANCES.pop(name, None)
    return None


def _app_destroyed(app_name) -> None:
    """Remove the application from the list."""
    _APP_INSTANCES.pop(app_name, None)


_APP_INITIALIZED = weakref.WeakSet[Application]()


def init_application(app: Application) -> Application:
    from himena._app_model.actions import ACTIONS, SUBMENUS
    from himena.widgets._main_window import MainWindow

    if app in _APP_INITIALIZED:
        return app

    app.register_actions(ACTIONS)
    app.menus.append_menu_items(SUBMENUS)
    app.destroyed.connect(_app_destroyed)
    _subs = ", ".join(menu.title for _, menu in SUBMENUS)
    _LOGGER.info(f"Initialized submenus: {_subs}")

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
    def _process_data_model(file_data: WidgetDataModel) -> None:
        _LOGGER.debug("processing %r", file_data)
        ins = current_instance(app.name)
        ins.add_data_model(file_data)
        return None

    @app.injection_store.mark_processor
    def _process_file_inputs(file_data: list[WidgetDataModel]) -> None:
        _LOGGER.debug("processing %r", file_data)
        for each in file_data:
            _process_data_model(each)

    @app.injection_store.mark_processor
    def _process_file_path(path: Path) -> None:
        if path is None:
            return None
        ins = current_instance(app.name)
        ins.read_file(path, plugin=None)
        return None

    @app.injection_store.mark_processor
    def _process_file_paths(paths: list[Path]) -> None:
        if paths:
            ins = current_instance(app.name)
            ins.read_files(paths)
        return None

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
        ins.add_function(fn, preview=fn.preview, title=fn.name)
        return None

    @app.injection_store.mark_processor
    def _process_parametric_widget(tup: ParametricWidgetTuple) -> None:
        if tup is None:
            return None
        tup = ParametricWidgetTuple(*tup)
        _LOGGER.debug("processing %r", tup)
        ins = current_instance(app.name)
        ins.add_parametric_widget(tup.widget, tup.callback, title=tup.title)

    _APP_INITIALIZED.add(app)
    return app
