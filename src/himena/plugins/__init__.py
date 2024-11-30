from typing import Callable, overload, TypeVar
from himena.plugins._checker import protocol_override
from himena.plugins._signature import configure_gui
from himena.plugins.io import register_reader_provider, register_writer_provider
from himena.plugins.actions import (
    register_function,
    register_dock_widget,
    configure_submenu,
    AppActionRegistry,
)
from himena.plugins.install import install_plugins

__all__ = [
    "protocol_override",
    "configure_gui",
    "get_plugin_interface",
    "install_plugins",
    "register_reader_provider",
    "register_writer_provider",
    "register_function",
    "register_dock_widget",
    "register_widget_class",
    "configure_submenu",
    "AppActionRegistry",
]

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
    import himena.qt

    return himena.qt.register_widget_class(type_, widget_class, priority=priority)
