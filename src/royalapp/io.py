from __future__ import annotations

from pathlib import Path
from typing import Callable, TypeVar
from royalapp.types import WidgetDataModel, ReaderFunction, WriterFunction
from royalapp.consts import BasicTextFileTypes

_ReaderProvider = Callable[[WidgetDataModel], ReaderFunction]
_WriterProvider = Callable[[WidgetDataModel], WriterFunction]

_RP = TypeVar("_RP", bound=_ReaderProvider)
_WP = TypeVar("_WP", bound=_WriterProvider)

_READER_PROVIDERS: list[_ReaderProvider] = []
_WRITER_PROVIDERS: list[_WriterProvider] = []


def get_readers(file_path: Path | list[Path]) -> list[ReaderFunction]:
    """Get reader."""
    matched: list[Callable] = []
    for provider in _READER_PROVIDERS:
        if out := provider(file_path):
            matched.append(out)
    if matched:
        return matched
    return [_fallback_reader(file_path)]


def get_writers(file_data: WidgetDataModel) -> list[WriterFunction]:
    """Get writer."""
    matched: list[WriterFunction] = []
    for provider in _WRITER_PROVIDERS:
        if out := provider(file_data):
            matched.append(out)
    if matched:
        return matched
    return [_fallback_writer(file_data)]


def register_reader_provider(provider: _RP) -> _RP:
    """Register reader provider function."""
    if not callable(provider):
        raise ValueError("Provider must be callable.")
    _READER_PROVIDERS.append(provider)
    return provider


def register_writer_provider(provider: _WP) -> _WP:
    """Register writer provider function."""
    if not callable(provider):
        raise ValueError("Provider must be callable.")
    _WRITER_PROVIDERS.append(provider)
    return provider


# default readers


def _read_text(file_path: Path) -> WidgetDataModel:
    """Read text file."""
    with open(file_path) as f:
        return WidgetDataModel(
            value=f.read(),
            type="text",
            source=Path(file_path),
        )


def _read_simple_image(file_path: Path) -> WidgetDataModel:
    """Read image file."""
    import imageio.v3 as iio

    return WidgetDataModel(
        value=iio.imread(file_path),
        type="image",
        source=Path(file_path),
    )


def _read_csv(file_path: Path) -> WidgetDataModel:
    """Read CSV file."""
    import numpy as np

    value = np.genfromtxt(file_path, delimiter=",", dtype=None, encoding=None)
    return WidgetDataModel(
        value,
        type="csv",
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
    elif file_path.suffix in {".png", ".jpg", ".jpeg", ".gif"}:
        return _read_simple_image
    raise ValueError(f"Unsupported file type: {file_path.suffix}")


# default writers


def write_text(file_data: WidgetDataModel[str]) -> None:
    """Write text file."""
    if file_data.source is None:
        raise ValueError("File path is not provided.")
    with open(file_data.source, "w") as f:
        f.write(file_data.value)


def _fallback_writer(file_data: WidgetDataModel) -> WriterFunction:
    """Get default writer."""
    if file_data.source.suffix in BasicTextFileTypes:
        return write_text
    else:
        return None
