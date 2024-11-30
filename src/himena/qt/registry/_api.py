from __future__ import annotations

from typing import Callable, TypeVar, overload, NamedTuple
from qtpy import QtWidgets as QtW

from himena.types import is_subtype
from himena.qt.registry._widgets import QFallbackWidget

WidgetClass = type[QtW.QWidget]


class WidgetClassTuple(NamedTuple):
    type: str
    widget_class: WidgetClass
    priority: int = 100


# NOTE: Different applications may use different widgets for the same data type.
_APP_TYPE_TO_QWIDGET: dict[str | None, list[WidgetClassTuple]] = {}

_F = TypeVar("_F", bound=WidgetClass)


@overload
def register_widget_class(
    type_: str,
    widget_class: _F,
    app: str | None,
    priority: int = 100,
) -> _F: ...


@overload
def register_widget_class(
    type_: str,
    widget_class: None,
    app: str | None,
    priority: int = 100,
) -> Callable[[_F], _F]: ...


def register_widget_class(type_, widget_class=None, app=None, priority=100):
    """
    Register a Qt widget class as a frontend widget for the given model type.

    Registered function must take `WidgetDataModel` as the only argument and return a
    `QtW.QWidget`. If `app` is given, the widget class is registered for the given app.
    Otherwise, the widget class is registered globally as a fallback widget class.

    >>> @register_widget("text")
    ... class MyTextEdit(QtW.QPlainTextEdit):
    ...     def update_model(self, model: WidgetDataModel):
    ...         self.setPlainText(model.value)
    """

    if app is not None and not isinstance(app, str):
        raise TypeError(f"App name must be a string, got {app!r}")
    if not isinstance(type_, str):
        raise TypeError(f"Type must be a string, got {type_!r}")

    def _inner(wdt_class):
        if not (isinstance(wdt_class, type) and issubclass(wdt_class, QtW.QWidget)):
            raise TypeError(
                "Widget class must be a subclass of `QtW.QWidget`, "
                f"got {wdt_class!r}"
            )
        if not hasattr(wdt_class, "update_model"):
            raise TypeError(
                f"Widget class {wdt_class!r} does not have a `update_model` method."
            )
        if app not in _APP_TYPE_TO_QWIDGET:
            _APP_TYPE_TO_QWIDGET[app] = []
        _APP_TYPE_TO_QWIDGET[app].append(WidgetClassTuple(type_, wdt_class, priority))
        return wdt_class

    return _inner if widget_class is None else _inner(widget_class)


def list_widget_class(
    app_name: str,
    type: str,
) -> tuple[list[WidgetClassTuple], type[QFallbackWidget]]:
    """List registered widget classes for the given app and super-type."""
    widget_list = _APP_TYPE_TO_QWIDGET.get(None, [])
    if app_name in _APP_TYPE_TO_QWIDGET:
        widget_list = _APP_TYPE_TO_QWIDGET[app_name] + widget_list
    return [
        item for item in widget_list if is_subtype(type, item.type)
    ], QFallbackWidget
