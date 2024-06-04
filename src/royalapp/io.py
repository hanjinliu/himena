from __future__ import annotations

from pathlib import Path
from typing import Callable, TypeVar
import warnings
from royalapp.types import WidgetDataModel, ReaderFunction, WriterFunction
from royalapp._utils import get_widget_data_model_variable

_ReaderProvider = Callable[["Path | list[Path]"], ReaderFunction]
_WriterProvider = Callable[[WidgetDataModel], WriterFunction]

_RP = TypeVar("_RP", bound=_ReaderProvider)
_WP = TypeVar("_WP", bound=_WriterProvider)

_READER_PROVIDERS: list[_ReaderProvider] = []
_WRITER_PROVIDERS: list[_WriterProvider] = []


def get_readers(file_path: Path | list[Path]) -> list[ReaderFunction]:
    """Get reader."""
    matched: list[ReaderFunction] = []
    for provider in _READER_PROVIDERS:
        try:
            out = provider(file_path)
        except Exception as e:
            _warn_failed_provider(provider, e)
        else:
            if out:
                if callable(out):
                    matched.append(out)
                else:
                    warnings.warn(
                        f"Reader provider {provider!r} returned {out!r}, which is not"
                        "callable."
                    )
    if matched:
        return matched
    raise ValueError(f"No reader functions supports file: {file_path.name}")


def get_writers(file_data: WidgetDataModel) -> list[WriterFunction]:
    """Get writer."""
    matched: list[WriterFunction] = []
    for provider in _WRITER_PROVIDERS:
        try:
            out = provider(file_data)
        except Exception as e:
            _warn_failed_provider(provider, e)
        else:
            if out:
                if callable(out):
                    matched.append(out)
                else:
                    warnings.warn(
                        f"Writer provider {provider!r} returned {out!r}, which is not"
                        "callable."
                    )
    if matched:
        return matched
    raise ValueError(f"No writer functions supports data: {file_data.type}")


def _warn_failed_provider(provider, e: Exception):
    return warnings.warn(
        f"Error in reader provider {provider!r}: {e}",
        RuntimeWarning,
        stacklevel=3,
    )


def register_reader_provider(provider: _RP) -> _RP:
    """
    Register reader provider function.

    This function should return a reader function for the given file path, or None if
    your plugin does not support the file type.

    >>> @register_reader_provider
    ... def my_reader_provider(path):
    ...     if Path(path).suffix != ".txt":
    ...         return None
    ...     def _read_text(path):  # this is the reader function
    ...         with open(path) as f:
    ...             return WidgetDataModel(value=f.read(), type="text", source=path)
    ...     return _read_text
    """
    if not callable(provider):
        raise ValueError("Provider must be callable.")
    _READER_PROVIDERS.append(provider)
    return provider


def register_writer_provider(provider: _WP) -> _WP:
    """
    Register writer provider function.

    This function should return a writer function for the given data model, or None if
    your plugin does not support the data type.

    >>> @register_writer_provider
    ... def my_writer_provider(model: WidgetDataModel):
    ...     if not isinstance(model.value, str) or model.source.suffix != ".txt":
    ...         return None
    ...     def _write_text(model: WidgetDataModel):  # this is the writer function
    ...         with open(model.source, "w") as f:
    ...             f.write(model.value)
    ...     return _write_text
    """
    if not callable(provider):
        raise ValueError("Provider must be callable.")
    _WRITER_PROVIDERS.append(TypedWriterProvider.try_convert(provider))
    return provider


class TypedWriterProvider:
    def __init__(self, func: Callable, typ: type):
        self._func = func
        self._data_type = typ

    def __call__(self, model: WidgetDataModel):
        if not isinstance(model.value, self._data_type):
            return None
        return self._func(model)

    @staticmethod
    def try_convert(func: Callable) -> Callable:
        if arg := get_widget_data_model_variable(func):
            return TypedWriterProvider(func, arg)
        return func
