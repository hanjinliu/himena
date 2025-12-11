from __future__ import annotations

from concurrent.futures import Future
from typing import TypeVar, TYPE_CHECKING
from logging import getLogger
import weakref
from magicgui.widgets import FunctionGui
from himena.consts import ParametricWidgetProtocolNames as PWPN
from himena.types import (
    Parametric,
    WidgetType,
    WidgetConstructor,
    WidgetDataModel,
    ClipboardDataModel,
    ParametricWidgetProtocol,
)
from himena.widgets._widget_list import TabArea
from himena.widgets._wrapper import SubWindow
from himena._utils import get_gui_config, ModelTrack
from himena.workflow import CommandExecution

if TYPE_CHECKING:
    from himena._app_model import HimenaApplication
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
        instance.tabs.clear()
        instance.dock_widgets.clear()


def _app_destroyed(app_name) -> None:
    """Remove the application from the list."""
    _APP_INSTANCES.pop(app_name, None)


_APP_INITIALIZED = weakref.WeakSet["HimenaApplication"]()


def init_application(app: HimenaApplication) -> HimenaApplication:
    """Register actions/menus and setup injection store."""
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

    ### providers ###
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

    @app.injection_store.mark_provider
    def _provide_data_model() -> WidgetDataModel:
        _LOGGER.debug("providing for %r", WidgetDataModel.__name__)
        return current_instance(app.name)._provide_file_output()[0]

    @app.injection_store.mark_provider
    def _get_clipboard_data() -> ClipboardDataModel:
        _LOGGER.debug("providing for %r", ClipboardDataModel.__name__)
        return current_instance(app.name).clipboard

    ### processors ###
    @app.injection_store.mark_processor
    def _process_data_model(model: WidgetDataModel) -> None:
        if not isinstance(model, WidgetDataModel):
            raise TypeError(f"Expected WidgetDataModel, got {type(model)}")
        ins = current_instance(app.name)
        if ins._instructions.process_model_output:
            _LOGGER.debug("processing %r", model)
            ins.add_data_model(model)

    @app.injection_store.mark_processor
    def _process_data_models(models: list[WidgetDataModel]) -> None:
        _LOGGER.debug("processing %r", models)
        for each in models:
            _process_data_model(each)

    @app.injection_store.mark_processor
    def _process_clipboard_data(clip_data: ClipboardDataModel) -> None:
        if clip_data is None:
            return None
        _LOGGER.debug("processing %r", clip_data)
        # set data to clipboard
        ins = current_instance(app.name)
        ins.clipboard = clip_data

    @app.injection_store.mark_processor
    def _process_parametric(fn: Parametric) -> None:
        if fn is None:
            return None
        _LOGGER.debug("processing %r", fn)
        ins = current_instance(app.name)
        gui_config = get_gui_config(fn)
        win = ins.add_function(fn, **gui_config)
        if win._is_run_immediately() and ins._instructions.gui_execution:
            try:
                win._widget_callback()
            finally:
                if win.is_alive:
                    win._close_me(ins)
        else:
            if (tracker := ModelTrack.get(fn)) and tracker.command_id:
                win._widget_workflow = CommandExecution(
                    command_id=tracker.command_id,
                    contexts=tracker.contexts,
                ).construct_workflow()

    @app.injection_store.mark_processor
    def _process_widget_type(widget: WidgetType) -> None:
        _LOGGER.debug("processing %r", widget)
        ins = current_instance(app.name)
        ins.add_widget(widget)

    @app.injection_store.mark_processor
    def _process_widget_constructor(con: WidgetConstructor) -> None:
        _LOGGER.debug("processing %r", con)
        ins = current_instance(app.name)
        ins.add_widget(con())

    @app.injection_store.mark_processor
    def _process_parametric_widget_protocol(widget: ParametricWidgetProtocol) -> None:
        if widget is None:
            return None
        _LOGGER.debug("processing %r", widget)
        ins = current_instance(app.name)
        if isinstance(widget, FunctionGui):
            widget.get_params = widget.asdict
            ins.add_parametric_widget(
                widget,
                callback=widget.__call__,
                title=widget.label,
                preview=False,
                auto_close=False,
                auto_size=False,
            )
        else:
            ins.add_parametric_widget(
                widget,
                title=getattr(widget, PWPN.GET_TITLE, lambda: None)(),
                preview=(
                    hasattr(widget, PWPN.IS_PREVIEW_ENABLED)
                    and hasattr(widget, PWPN.CONNECT_CHANGED_SIGNAL)
                ),
                auto_close=getattr(widget, PWPN.GET_AUTO_CLOSE, lambda: True)(),
                auto_size=getattr(widget, PWPN.GET_AUTO_SIZE, lambda: True)(),
            )

    @app.injection_store.mark_processor
    def _process_future(future: Future) -> None:
        ui = current_instance(app.name)
        if ui._instructions.unwrap_future:
            app._future_done_callback(future)
        else:
            cb = ui._backend_main_window._process_future_done_callback(
                app._future_done_callback, lambda *_: None
            )
            future.add_done_callback(cb)
            app._futures.add(future)

    _APP_INITIALIZED.add(app)
    return app
