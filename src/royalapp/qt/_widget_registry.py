from __future__ import annotations
from typing import Callable, Hashable, TypeVar, overload
from qtpy import QtWidgets as QtW

from royalapp.types import FileData

WidgetProvider = Callable[[FileData], QtW.QWidget]

# TODO: split _TYPE_TO_QWIDGET for each app
_TYPE_TO_QWIDGET: dict[Hashable, WidgetProvider] = {}

_F = TypeVar("_F", bound=WidgetProvider)


@overload
def register_widget_provider(
    file_type: Hashable,
    widget_provider: _F,
) -> _F: ...


@overload
def register_widget_provider(
    file_type: Hashable,
    widget_provider: None,
) -> Callable[[_F], _F]: ...


def register_widget_provider(file_type, widget_provider=None) -> None:
    """
    Register a widget provider function for a file type.

    Registered function must take `FileData` as the only argument and return a
    `QtW.QWidget`.

    >>> @register_widget_provider("text")
    ... class MyTextEdit(QtW.QPlainTextEdit):
    ...     def __init__(self, fd: FileData):
    ...         super().__init__()
    ...         self.setPlainText(fd.value)

    >>> @register_widget_provider("text", lambda fd: QtW.QLabel(fd.value))
    """

    def _inner(widget_provider):
        _TYPE_TO_QWIDGET[file_type] = widget_provider
        return widget_provider

    if widget_provider is None:
        return _inner
    return _inner(widget_provider)


class QDefaultTextEdit(QtW.QPlainTextEdit):
    def __init__(self, file: FileData):
        super().__init__()
        self.setPlainText(file.value)
        if file.file_path is not None:
            self.setObjectName(file.file_path.name)
        self._file_path = file.file_path
        self.textChanged.connect(self._on_text_changed)

    def _on_text_changed(self) -> None:
        # self.setWindowModified(True)
        pass

    def as_file_data(self) -> FileData:
        return FileData(
            value=self.toPlainText(),
            file_type="text",
            file_path=self._file_path,
        )


def _prep_plain_text_edit(file: FileData) -> QtW.QPlainTextEdit:
    """Prepare a plain text edit widget."""
    widget = QDefaultTextEdit(file)
    return widget


def register_default_widget_types() -> None:
    """Register default widget types."""
    register_widget_provider(str, _prep_plain_text_edit)
    register_widget_provider("text", _prep_plain_text_edit)


def pick_provider(file: FileData) -> WidgetProvider:
    """Pick a widget provider for the file."""
    return _TYPE_TO_QWIDGET[file.file_type]


register_default_widget_types()
