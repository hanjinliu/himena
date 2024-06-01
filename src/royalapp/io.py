from __future__ import annotations

from pathlib import Path
from typing import Callable, TypeVar
import warnings
from royalapp.types import WidgetDataModel, ReaderFunction, WriterFunction
from royalapp.consts import BasicTextFileTypes, StandardTypes
from royalapp._utils import get_widget_data_model_variable

_ReaderProvider = Callable[[Path], ReaderFunction]
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
                matched.append(out)
    if matched:
        return matched
    return [_fallback_reader(file_path)]


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
                matched.append(out)
    if matched:
        return matched
    return [_fallback_writer(file_data)]


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


# default readers


def _read_text(file_path: Path) -> WidgetDataModel:
    """Read text file."""
    with open(file_path) as f:
        return WidgetDataModel(
            value=f.read(),
            type=StandardTypes.TEXT,
            source=Path(file_path),
        )


def _read_simple_image(file_path: Path) -> WidgetDataModel:
    """Read image file."""
    import numpy as np
    from PIL import Image

    arr = np.array(Image.open(file_path))

    return WidgetDataModel(
        value=arr,
        type=StandardTypes.IMAGE,
        source=Path(file_path),
    )


def _read_csv(file_path: Path) -> WidgetDataModel:
    """Read CSV file."""
    import csv

    with open(file_path) as f:
        reader = csv.reader(f)
        data = list(reader)

    return WidgetDataModel(
        value=data,
        type=StandardTypes.TABLE,
        source=Path(file_path),
    )


def _fallback_reader(file_path: Path | list[Path]) -> ReaderFunction:
    """Get default reader."""
    if isinstance(file_path, list):
        raise ValueError("Multiple files are not supported.")
    if file_path.suffix in BasicTextFileTypes:
        return _read_text
    elif file_path.suffix == ".csv":
        return _read_csv
    elif file_path.suffix in {".png", ".jpg", ".jpeg"}:
        return _read_simple_image
    raise ValueError(f"Unsupported file type: {file_path.suffix}")


# default writers


def _write_text(file_data: WidgetDataModel[str]) -> None:
    """Write text file."""
    if file_data.source is None:
        raise ValueError("File path is not provided.")
    with open(file_data.source, "w") as f:
        f.write(file_data.value)


def _fallback_writer(file_data: WidgetDataModel) -> WriterFunction:
    """Get default writer."""
    if file_data.source.suffix in BasicTextFileTypes:
        return _write_text
    else:
        return None


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
