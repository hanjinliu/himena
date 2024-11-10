from __future__ import annotations

from pathlib import Path
from logging import getLogger
from typing import TypeVar, NamedTuple
import warnings
from himena.types import (
    WidgetDataModel,
    ReaderFunction,
    WriterFunction,
    ReaderProvider,
    WriterProvider,
)

_LOGGER = getLogger(__name__)


class PluginInfo(NamedTuple):
    module: str
    name: str

    def to_str(self) -> str:
        """Return the string representation of the plugin."""
        return f"{self.module}.{self.name}"


class ReaderProviderTuple(NamedTuple):
    provider: ReaderProvider
    priority: int
    plugin: PluginInfo | None = None


class WriterProviderTuple(NamedTuple):
    provider: WriterProvider
    priority: int
    plugin: PluginInfo | None = None


class ReaderTuple(NamedTuple):
    reader: ReaderFunction
    priority: int
    plugin: PluginInfo | None = None

    def read(self, path: str | Path) -> WidgetDataModel:
        out = self.reader(Path(path))
        if not isinstance(out, WidgetDataModel):
            raise TypeError(
                f"Reader function {self.reader!r} did not return a WidgetDataModel."
            )
        return out


class WriterTuple(NamedTuple):
    writer: WriterFunction
    priority: int
    plugin: PluginInfo | None = None

    def write(self, model: WidgetDataModel, path: str | Path):
        return self.writer(model, Path(path))


_READER_PROVIDERS: list[ReaderProviderTuple] = []
_WRITER_PROVIDERS: list[WriterProviderTuple] = []
_T = TypeVar("_T", ReaderTuple, WriterTuple)


def get_readers(path: Path | list[Path], empty_ok: bool = False) -> list[ReaderTuple]:
    """Get reader functions that can read the path(s)."""
    matched: list[ReaderTuple] = []
    for info in _READER_PROVIDERS:
        try:
            out = info.provider(path)
        except Exception as e:
            _warn_failed_provider(info.provider, e)
        else:
            if out:
                if callable(out):
                    matched.append(ReaderTuple(out, info.priority, info.plugin))
                else:
                    warnings.warn(
                        f"Reader provider {info.provider!r} returned {out!r}, which is "
                        "not callable."
                    )
    if not matched and not empty_ok:
        if isinstance(path, list):
            msg = [p.name for p in path]
        else:
            msg = path.name
        raise ValueError(f"No reader functions available for {msg!r}")
    return matched


def get_writers(model: WidgetDataModel, empty_ok: bool = False) -> list[WriterTuple]:
    """Get writer functions that can write given data model."""
    matched: list[WriterTuple] = []
    for info in _WRITER_PROVIDERS:
        try:
            out = info.provider(model)
        except Exception as e:
            _warn_failed_provider(info.provider, e)
        else:
            if out:
                if callable(out):
                    matched.append(WriterTuple(out, info.priority, info.plugin))
                else:
                    warnings.warn(
                        f"Writer provider {info.provider!r} returned {out!r}, which is "
                        "not callable."
                    )
    if not matched and not empty_ok:
        _LOGGER.info("Writer providers: %r", [x[0] for x in _WRITER_PROVIDERS])
        raise ValueError(f"No writer functions available for {model.type!r}")
    return matched


def _pick_by_priority(tuples: list[_T]) -> _T:
    return max(tuples, key=lambda x: x.priority)


def pick_reader(path: Path, plugin: str | None = None) -> ReaderTuple:
    """Pick a reader for the given path."""
    readers = get_readers(path)
    if plugin is None:
        reader = _pick_by_priority(readers)
    else:
        for each in readers:
            if each.plugin == plugin:
                reader = each
                break
        else:
            warnings.warn(
                f"Plugin {plugin} not found, using default writer.",
                UserWarning,
                stacklevel=2,
            )
            reader = _pick_by_priority(readers)
    return reader


def pick_writer(model: WidgetDataModel, plugin: str | None = None) -> WriterTuple:
    """Pick a writer for the given data model."""
    writers = get_writers(model)
    if plugin is None:
        writer = _pick_by_priority(writers)
    else:
        for each in writers:
            if each.plugin == plugin:
                writer = each
                break
        else:
            warnings.warn(
                f"Plugin {plugin} not found, using default writer.",
                UserWarning,
                stacklevel=2,
            )
            writer = _pick_by_priority(writers)
    return writer


def read(path: Path, plugin: str | None = None) -> WidgetDataModel:
    """Read the file at the given path."""
    return pick_reader(path, plugin=plugin).read(path)


def write(model: WidgetDataModel, path: Path, plugin: str | None = None):
    """Write the data model to the given path."""
    return pick_writer(model, plugin=plugin).write(model, path)


def _warn_failed_provider(provider, e: Exception):
    return warnings.warn(
        f"Error in reader provider {provider!r}: {e}",
        RuntimeWarning,
        stacklevel=3,
    )
