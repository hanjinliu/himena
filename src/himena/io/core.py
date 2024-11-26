from __future__ import annotations

from pathlib import Path
from logging import getLogger
from typing import Generic, TypeVar, TYPE_CHECKING
import warnings
from himena.io._tuples import (
    ReaderProviderTuple,
    WriterProviderTuple,
    ReaderTuple,
    WriterTuple,
    PluginInfo,
)
from himena.types import WidgetDataModel

if TYPE_CHECKING:
    from typing import Self

_LOGGER = getLogger(__name__)
_S = TypeVar("_S", ReaderProviderTuple, WriterProviderTuple)
_T = TypeVar("_T", ReaderTuple, WriterTuple)


class ProviderStore(Generic[_S]):
    _global_instance = None

    def __init__(self):
        self._providers: list[_S] = []

    @classmethod
    def instance(cls) -> Self:
        if cls._global_instance is None:
            cls._global_instance = cls()
        return cls._global_instance


class ReaderProviderStore(ProviderStore[ReaderProviderTuple]):
    def add(self, provider, priority: int, plugin: str | None = None):
        tup = ReaderProviderTuple(provider, priority, plugin)
        self._providers.append(tup)

    def get(
        self,
        path: Path | list[Path],
        empty_ok: bool = False,
        min_priority: int = 0,
    ) -> list[ReaderTuple]:
        matched: list[ReaderTuple] = []
        for info in self._providers:
            if info.priority < min_priority:
                continue
            try:
                out = info.provider(path)
            except Exception as e:
                _warn_failed_provider(info.provider, e)
            else:
                if out is None:
                    _LOGGER.debug("Reader provider %r did not match", info.provider)
                elif callable(out):
                    matched.append(ReaderTuple(out, info.priority, info.plugin))
                else:
                    _LOGGER.warning(
                        f"Reader provider {info.provider!r} returned {out!r}, which "
                        "is not callable."
                    )
        _LOGGER.debug("Matched reader providers: %r", [x[0] for x in matched])
        if not matched and not empty_ok:
            if isinstance(path, list):
                msg = [p.name for p in path]
            else:
                msg = path.name
            raise ValueError(f"No reader functions available for {msg!r}")
        return matched

    def pick(
        self,
        path: Path,
        *,
        plugin: str | None = None,
        min_priority: int = 0,
    ) -> ReaderTuple:
        """Pick a reader that match the inputs."""
        if plugin is not None:
            # if plugin is given, force to use it
            min_priority = -float("inf")
        return _pick_from_list(self.get(path, min_priority=min_priority), plugin)

    def run(
        self,
        path: Path,
        *,
        plugin: str | None = None,
    ) -> WidgetDataModel:
        reader = self.pick(path, plugin=plugin, min_priority=-float("inf"))
        return reader.read(path)


class WriterProviderStore(ProviderStore[WriterProviderTuple]):
    def add(self, provider, priority: int, plugin: str | None = None):
        tup = WriterProviderTuple(provider, priority, plugin)
        self._providers.append(tup)

    def get(
        self,
        model: WidgetDataModel,
        empty_ok: bool = False,
        min_priority: int = 0,
    ) -> list[WriterTuple]:
        matched: list[WriterTuple] = []
        for info in self._providers:
            if info.priority < min_priority:
                continue
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
            _LOGGER.info("Writer providers: %r", [x[0] for x in self._providers])
            raise ValueError(f"No writer functions available for {model.type!r}")
        return matched

    def pick(
        self,
        model: WidgetDataModel,
        plugin: str | None = None,
        min_priority: int = 0,
    ) -> WriterTuple:
        """Pick a writer that match the inputs to write the model."""
        if plugin is not None:
            # if plugin is given, force to use it
            min_priority = -float("inf")
        return _pick_from_list(self.get(model, min_priority=min_priority), plugin)

    def run(
        self, model: WidgetDataModel, path: Path, *, plugin: str | None = None
    ) -> None:
        writer = self.pick(model, plugin=plugin, min_priority=-float("inf"))
        return writer.write(model, path)


def _pick_by_priority(tuples: list[_T]) -> _T:
    return max(tuples, key=lambda x: x.priority)


def _pick_from_list(choices: list[_T], plugin: str | None) -> _T:
    if plugin is None:
        out = _pick_by_priority(choices)
    else:
        plugin_info = PluginInfo.from_str(plugin)
        for each in choices:
            if each.plugin == plugin_info:
                out = each
                break
        else:
            _LOGGER.warning(f"Plugin {plugin} not found, using the default one.")
            out = _pick_by_priority(choices)
    return out


def _warn_failed_provider(provider, e: Exception):
    return _LOGGER.error(f"Error in reader provider {provider!r}: {e}")


def read_and_update_source(reader: ReaderTuple, source: Path) -> WidgetDataModel:
    """Update the `method` attribute if it is not set."""
    model = reader.read(source)
    if model.method is None:
        model = model._with_source(source=source, plugin=reader.plugin)
    return model
