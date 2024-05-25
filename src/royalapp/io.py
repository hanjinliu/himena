from __future__ import annotations

from pathlib import Path
from typing import Callable
from royalapp.types import FileData
from royalapp.consts import BasicTextFileTypes

_READER_PROVIDERS: list[Callable] = []


def get_readers(file_path: Path | list[Path]) -> list[Callable[..., FileData]]:
    """Get reader."""
    matched: list[Callable] = []
    for provider in _READER_PROVIDERS:
        if out := provider(file_path):
            matched.append(out)
    if matched:
        return matched
    return [_fallback_reader(file_path)]


_WRITER_PROVIDERS: list[Callable] = []


def get_writers(file_path: Path) -> list[Callable[..., None]]:
    """Get writer."""
    matched: list[Callable] = []
    for provider in _WRITER_PROVIDERS:
        if out := provider(file_path):
            matched.append(out)
    if matched:
        return matched
    return [_fallback_writer(file_path)]


# default readers


def _read_text(file_path: Path) -> FileData:
    """Read text file."""
    with open(file_path) as f:
        return FileData(
            value=f.read(),
            file_type="text",
            file_path=Path(file_path),
        )


def _read_simple_image(file_path: Path) -> FileData:
    """Read image file."""
    import imageio.v3 as iio

    return FileData(
        value=iio.imread(file_path),
        file_type="image",
        file_path=Path(file_path),
    )


def _read_csv(file_path: Path) -> FileData:
    """Read CSV file."""
    import numpy as np

    value = np.genfromtxt(file_path, delimiter=",", dtype=None, encoding=None)
    return FileData(
        value,
        file_type="csv",
        file_path=Path(file_path),
    )


def _fallback_reader(file_path: Path | list[Path]) -> Callable[..., FileData]:
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


def write_text(file_path: Path, data: str) -> None:
    """Write text file."""
    with open(file_path, "w") as f:
        f.write(data)


def _fallback_writer(file_path: Path) -> Callable[..., None]:
    """Get default writer."""
    if file_path.suffix in BasicTextFileTypes:
        return write_text
    else:
        return None
