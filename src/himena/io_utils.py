"""A GUI-independent utility functions to read/write files."""

from __future__ import annotations

from pathlib import Path
from himena.types import WidgetDataModel
from himena._providers import ReaderProviderStore, WriterProviderStore, ReaderTuple


def read(
    path: str | Path,
    *,
    plugin: str | None = None,
) -> WidgetDataModel:
    """Read a file as a data model."""
    ins = ReaderProviderStore.instance()
    return ins.run(Path(path), plugin=plugin)


def get_readers(path: str | Path, min_priority: int = 0) -> list[ReaderTuple]:
    """Get the list of readers that can read the file."""
    ins = ReaderProviderStore.instance()
    return ins.get(Path(path), empty_ok=True, min_priority=min_priority)


def write(
    model: WidgetDataModel,
    path: str | Path,
    *,
    plugin: str | None = None,
) -> None:
    """Write a data model to a file."""
    ins = WriterProviderStore.instance()
    path = Path(path)
    if path.suffix == ".pickle":
        ins.run(model, path, plugin=plugin)
    else:
        ins.run(model, path, plugin=plugin, min_priority=0)
    return None
