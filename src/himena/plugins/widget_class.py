from types import MappingProxyType
from typing import Callable, overload, TypeVar, TYPE_CHECKING
from app_model.types import Action
from himena._descriptors import NoNeedToSave
from himena._utils import get_display_name, get_widget_class_id
from himena._app_model import AppContext as ctx
from himena.plugins.actions import AppActionRegistry, _type_to_expression

from himena.types import WidgetDataModel

if TYPE_CHECKING:
    from himena.widgets import SubWindow, MainWindow

_T = TypeVar("_T")
_WIDGET_ID_TO_WIDGET_CLASS: dict[str, type] = {}


def get_widget_class(id: str) -> type | None:
    return _WIDGET_ID_TO_WIDGET_CLASS.get(id)


@overload
def register_widget_class(
    type_: str,
    widget_class: _T,
    priority: int = 100,
) -> _T: ...


@overload
def register_widget_class(
    type_: str,
    widget_class: None,
    priority: int = 100,
) -> Callable[[_T], _T]: ...


def register_widget_class(type_, widget_class=None, priority=100):
    """Register a frontend widget class for the given model type.

    The `__init__` method of the registered class must not take any argument. The class
    must implement `update_model` method to update the widget state from a
    WidgetDataModel.

    ``` python
    @register_widget("text")
    class MyTextEdit(QtW.QPlainTextEdit):
        def update_model(self, model: WidgetDataModel):
            self.setPlainText(model.value)
    ```

    There are other method names that can be implemented to make the widget more
    functional.

    - `to_model(self) -> WidgetDataModel`:
    - `model_type(self) -> str`:
    - `control_widget(self) -> <widget>`:
    - `is_modified(self) -> bool`:
    - `set_modified(self, modified: bool)`:
    - `size_hint(self) -> tuple[int, int]`:
    - `is_editable(self) -> bool`:
    - `set_editable(self, editable: bool)`:
    - `dropped_callback(self, other: WidgetDataModel)`:
    - `allowed_drop_types(self) -> list[str]`:
    - `display_name(cls) -> str`:
    - `theme_changed_callback(self, theme: Theme)`:
    - `widget_activated_callback(self)`:
    - `widget_closed_callback(self)`:
    - `widget_resized_callback(self, size_old, size_new)`:
    """

    def inner(wcls):
        import himena.qt

        widget_id = get_widget_class_id(wcls)
        if existing_class := _WIDGET_ID_TO_WIDGET_CLASS.get(widget_id):
            raise ValueError(
                f"Widget class with ID {widget_id!r} already exists ({existing_class})."
            )
        _WIDGET_ID_TO_WIDGET_CLASS[widget_id] = wcls
        himena.qt.register_widget_class(type_, wcls, priority=priority)
        fn = OpenDataInFunction(type_, wcls)
        AppActionRegistry.instance().add_action(fn.to_action())
        wcls.__himena_model_type__ = type_
        return wcls

    return inner if widget_class is None else inner(widget_class)


def widget_classes() -> MappingProxyType[str, type]:
    """Get the mapping of widget ID to widget class."""
    from himena.qt.registry._api import _APP_TYPE_TO_QWIDGET

    out = {}
    for widget_list in _APP_TYPE_TO_QWIDGET.values():
        for item in widget_list:
            out[item.type] = item.widget_class
    return MappingProxyType(out)


def register_previewer_class(type_: str, widget_class: type):
    """Register a widget class for previewing the given model type."""

    def inner(wcls):
        import himena.qt

        widget_id = get_widget_class_id(wcls)
        if existing_class := _WIDGET_ID_TO_WIDGET_CLASS.get(widget_id):
            raise ValueError(
                f"Widget class with ID {widget_id!r} already exists ({existing_class})."
            )
        _WIDGET_ID_TO_WIDGET_CLASS[widget_id] = wcls
        himena.qt.register_widget_class(type_, wcls, priority=-10)
        fn = OpenDataInFunction(type_, wcls)
        AppActionRegistry.instance().add_action(fn.to_action())
        fn = PreviewDataInFunction(type_, wcls)
        AppActionRegistry.instance().add_action(fn.to_action())
        return type_

    return inner if widget_class is None else inner(widget_class)


class OpenDataInFunction:
    """Callable class for 'open this data in ...' action."""

    def __init__(self, type_: str, widget_class: type):
        self._display_name = get_display_name(widget_class)
        self._plugin_id = get_widget_class_id(widget_class)
        self._action_id = "open-in:" + self._plugin_id
        self._type = type_
        self._enablement = (
            # disable action if the model data type is different
            _type_to_expression(self._type)
            # disable action that open the same data in the same widget
            & (ctx.active_window_widget_id != self._plugin_id)
        )

    def __call__(self, model: WidgetDataModel) -> WidgetDataModel:
        return model.with_open_plugin(
            self._plugin_id, save_behavior_override=NoNeedToSave()
        )

    def to_action(self) -> Action:
        return Action(
            id=self._action_id,
            title=self._display_name,
            tooltip=f"Open this data in {self._display_name}",
            callback=self,
            enablement=self._enablement,
            menus=[{"id": f"/open-in/{self._type}", "group": "open-in"}],
        )


class PreviewDataInFunction:
    """Callable class for 'preview this data in ...' action."""

    def __init__(self, type_: str, widget_class: type):
        self._display_name = get_display_name(widget_class)
        self._plugin_id = get_widget_class_id(widget_class)
        self._action_id = "preview-in:" + self._plugin_id
        self._type = type_

    def __call__(self, win: "SubWindow", ui: "MainWindow"):
        model = win.to_model().with_open_plugin(self._plugin_id)
        previewer = ui.add_data_model(model)
        previewer._switch_to_file_watch_mode()
        return None

    def menu_id(self) -> str:
        return f"/model_menu:{self._type}/preview-in"

    def to_action(self) -> Action:
        tooltip = f"Preview this data in {self._display_name}"
        return Action(
            id=self._action_id,
            title=self._display_name,
            tooltip=tooltip,
            callback=self,
            menus=[{"id": self.menu_id(), "group": "open-in"}],
        )
