from __future__ import annotations
from typing import Callable, Hashable, TypeVar, Union, overload
from qtpy import QtWidgets as QtW

from royalapp.types import WidgetDataModel
from royalapp.qt.registry._widgets import QFallbackWidget

WidgetClass = Union[Callable[[WidgetDataModel], QtW.QWidget], type[QtW.QWidget]]

_GLOBAL_TYPE_TO_QWIDGET: dict[Hashable, WidgetClass] = {}
_APP_TYPE_TO_QWIDGET: dict[str, dict[Hashable, WidgetClass]] = {}

_F = TypeVar("_F", bound=WidgetClass)


@overload
def register_frontend_widget(
    type_: Hashable,
    widget_class: _F,
    app: str | None,
    override: bool = True,
) -> _F: ...


@overload
def register_frontend_widget(
    type_: Hashable,
    widget_class: None,
    app: str | None,
    override: bool = True,
) -> Callable[[_F], _F]: ...


def register_frontend_widget(
    type_,
    widget_class=None,
    app=None,
    override=True,
) -> None:
    """
    Register a widget class as a frontend widget for the given file type.

    Registered function must take `WidgetDataModel` as the only argument and return a
    `QtW.QWidget`. If `app` is given, the widget class is registered for the given app.
    Otherwise, the widget class is registered globally as a fallback widget class.

    >>> @register_frontend_widget("text")
    ... class MyTextEdit(QtW.QPlainTextEdit):
    ...     @classmethod
    ...     def from_model(cls, fd: WidgetDataModel):
    ...         self = cls()
    ...         self.setPlainText(fd.value)
    ...         return self
    """

    if app is not None and not isinstance(app, str):
        raise TypeError(f"App name must be a string, got {app!r}")

    def _inner(wdt_class):
        if not (isinstance(wdt_class, type) and issubclass(wdt_class, QtW.QWidget)):
            raise TypeError(
                "Widget class must be a subclass of `QtW.QWidget`, "
                f"got {wdt_class!r}"
            )
        if not hasattr(wdt_class, "from_model"):
            raise TypeError(
                f"Widget class {wdt_class!r} does not have an `from_model` method."
            )
        if app is not None:
            if app not in _APP_TYPE_TO_QWIDGET:
                _APP_TYPE_TO_QWIDGET[app] = {}
            if type_ not in _APP_TYPE_TO_QWIDGET[app] or override:
                _APP_TYPE_TO_QWIDGET[app][type_] = wdt_class
        else:
            if type_ not in _GLOBAL_TYPE_TO_QWIDGET or override:
                _GLOBAL_TYPE_TO_QWIDGET[type_] = wdt_class
        return wdt_class

    return _inner if widget_class is None else _inner(widget_class)


def pick_widget_class(app_name: str, type: Hashable) -> WidgetClass:
    """Pick a widget class for the given file type."""
    if app_name in _APP_TYPE_TO_QWIDGET:
        _map_for_app = _APP_TYPE_TO_QWIDGET[app_name]
        if type in _map_for_app:
            return _map_for_app[type]
    if type not in _GLOBAL_TYPE_TO_QWIDGET:
        return QFallbackWidget
    return _GLOBAL_TYPE_TO_QWIDGET[type]
