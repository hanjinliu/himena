from __future__ import annotations
from typing import Callable, Hashable, TypeVar, Union, overload
from qtpy import QtWidgets as QtW

from royalapp.types import WidgetDataModel

WidgetClass = Union[Callable[[WidgetDataModel], QtW.QWidget], type[QtW.QWidget]]

# TODO: split _TYPE_TO_QWIDGET for each app
_TYPE_TO_QWIDGET: dict[Hashable, WidgetClass] = {}

_F = TypeVar("_F", bound=WidgetClass)


@overload
def register_frontend_widget(
    type_: Hashable,
    widget_class: _F,
) -> _F: ...


@overload
def register_frontend_widget(
    type_: Hashable,
    widget_class: None,
) -> Callable[[_F], _F]: ...


def register_frontend_widget(type_, widget_class=None) -> None:
    """
    Register a widget class as a frontend widget for the given file type.

    Registered function must take `FileData` as the only argument and return a
    `QtW.QWidget`.

    >>> @register_frontend_widget("text")
    ... class MyTextEdit(QtW.QPlainTextEdit):
    ...     @classmethod
    ...     def (cls, fd: FileData):
    ...         self = cls()
    ...         self.setPlainText(fd.value)
    ...         return self
    """

    def _inner(widget_class):
        _TYPE_TO_QWIDGET[type_] = widget_class
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
        return widget_class

    if widget_class is None:
        return _inner
    return _inner(widget_class)


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


def register_default_widget_types() -> None:
    """Register default widget types."""
    register_frontend_widget(str, QDefaultTextEdit)
    register_frontend_widget("text", QDefaultTextEdit)


def pick_widget_class(type: Hashable) -> WidgetClass:
    """Pick a widget class for the given file type."""
    if type not in _TYPE_TO_QWIDGET:
        raise ValueError(f"No widget class is registered for file type {type!r}")
    return _TYPE_TO_QWIDGET[type]


def provide_widget(fd: WidgetDataModel) -> QtW.QWidget:
    """Provide a widget for the file."""
    widget_class = pick_widget_class(fd.type)
    return widget_class.from_model(fd)


register_default_widget_types()
