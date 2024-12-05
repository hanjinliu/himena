from typing import Callable, overload, TypeVar
from app_model.types import Action
from himena._descriptors import NoNeedToSave
from himena._utils import get_display_name
from himena.plugins.actions import AppActionRegistry
from himena.types import WidgetDataModel

_T = TypeVar("_T")


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
    """
    Register a Qt widget class as a widget for the given model type.

    Registered class must implements `update_model` method to interpret the content of
    the incoming `WidgetDataModel`

    Examples
    --------
    >>> @register_widget("text")
    ... class MyTextEdit(QtW.QPlainTextEdit):
    ...     def update_model(self, model: WidgetDataModel):
    ...         self.setPlainText(model.value)
    """

    def inner(wcls):
        import himena.qt

        himena.qt.register_widget_class(type_, wcls, priority=priority)
        fn = OpenDataInFunction(type_, wcls)
        AppActionRegistry.instance().add_action(fn.to_action())
        return type_

    return inner if widget_class is None else inner(widget_class)


class OpenDataInFunction:
    """Callable class for 'open this data in ...' action."""

    def __init__(self, type_: str, widget_class: type):
        self._display_name = get_display_name(widget_class)
        self._plugin_id = f"{widget_class.__module__}.{widget_class.__name__}"
        self._type = type_

    def __call__(self, model: WidgetDataModel) -> WidgetDataModel:
        return model.with_open_plugin(
            self._plugin_id, save_behavior_override=NoNeedToSave()
        )

    def menu_id(self) -> str:
        return f"/model_menu:{self._type}/open-in"

    def to_action(self) -> Action:
        tooltip = f"Open this data in {self._display_name}"
        return Action(
            id=self._plugin_id,
            title=self._display_name,
            tooltip=tooltip,
            callback=self,
            menus=[{"id": self.menu_id(), "group": "open-in"}],
        )
