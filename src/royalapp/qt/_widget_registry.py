from __future__ import annotations
from typing import Callable, Hashable, TypeVar, Union, overload
from qtpy import QtWidgets as QtW

from royalapp.types import WidgetDataModel

WidgetClass = Union[Callable[[WidgetDataModel], QtW.QWidget], type[QtW.QWidget]]

_GLOBAL_TYPE_TO_QWIDGET: dict[Hashable, WidgetClass] = {}
_APP_TYPE_TO_QWIDGET: dict[str, dict[Hashable, WidgetClass]] = {}

_F = TypeVar("_F", bound=WidgetClass)


@overload
def register_frontend_widget(
    type_: Hashable,
    app: str | None,
    widget_class: _F,
) -> _F: ...


@overload
def register_frontend_widget(
    type_: Hashable,
    app: str | None,
    widget_class: None,
) -> Callable[[_F], _F]: ...


def register_frontend_widget(type_, app=None, widget_class=None) -> None:
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

    def _inner(widget_class):
        if not (
            isinstance(widget_class, type) and issubclass(widget_class, QtW.QWidget)
        ):
            raise TypeError(
                "Widget class must be a subclass of `QtW.QWidget`, "
                f"got {widget_class!r}"
            )
        if not hasattr(widget_class, "from_model"):
            raise TypeError(
                f"Widget class {widget_class!r} does not have an `from_model` method."
            )
        if app is not None:
            if app not in _APP_TYPE_TO_QWIDGET:
                _APP_TYPE_TO_QWIDGET[app] = {}
            _APP_TYPE_TO_QWIDGET[app][type_] = widget_class
        else:
            _GLOBAL_TYPE_TO_QWIDGET[type_] = widget_class
        return widget_class

    return _inner if widget_class is None else _inner(widget_class)


class QDefaultTextEdit(QtW.QPlainTextEdit):
    def __init__(self, file_path):
        super().__init__()
        self._file_path = file_path
        self.textChanged.connect(self._on_text_changed)

    def _on_text_changed(self) -> None:
        # self.setWindowModified(True)
        pass

    @classmethod
    def from_model(cls, file: WidgetDataModel) -> QDefaultTextEdit:
        self = cls(file.source)
        self.setPlainText(file.value)
        if file.source is not None:
            self.setObjectName(file.source.name)
        return self

    def to_model(self) -> WidgetDataModel:
        return WidgetDataModel(
            value=self.toPlainText(),
            type="text",
            source=self._file_path,
        )


class QFallbackWidget(QtW.QPlainTextEdit):
    """A fallback widget for the data of non-registered type."""

    def __init__(self):
        super().__init__()
        self.setReadOnly(True)

    @classmethod
    def from_model(cls, model: WidgetDataModel) -> QFallbackWidget:
        self = cls()
        self.setPlainText(f"No widget registered for the data:\n\n{model.value!r}")
        return self


def register_default_widget_types() -> None:
    """Register default widget types."""
    register_frontend_widget(str, QDefaultTextEdit)
    register_frontend_widget("text", QDefaultTextEdit)


def pick_widget_class(app_name: str, type: Hashable) -> WidgetClass:
    """Pick a widget class for the given file type."""
    if app_name in _APP_TYPE_TO_QWIDGET:
        _map = _APP_TYPE_TO_QWIDGET[app_name]
        if type in _map:
            return _map[type]
    if type not in _GLOBAL_TYPE_TO_QWIDGET:
        return QFallbackWidget
    return _GLOBAL_TYPE_TO_QWIDGET[type]


register_default_widget_types()
