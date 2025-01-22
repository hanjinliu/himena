from __future__ import annotations

from pathlib import Path
from logging import getLogger
from typing import Generic, Iterator, TypeVar, TYPE_CHECKING
import warnings
from himena.utils.misc import PluginInfo
from himena.types import WidgetDataModel

if TYPE_CHECKING:
    from typing import Self
    from himena.plugins.io import ReaderPlugin, WriterPlugin, _IOPluginBase

    PathOrPaths = str | Path | list[str | Path]

_LOGGER = getLogger(__name__)
_S = TypeVar("_S", bound="_IOPluginBase")


class ProviderStore(Generic[_S]):
    _global_instance = None

    def __init__(self):
        self._plugin_items: list[_S] = []

    @classmethod
    def instance(cls) -> Self:
        if cls._global_instance is None:
            cls._global_instance = cls()
        return cls._global_instance


class ReaderProviderStore(ProviderStore["ReaderPlugin"]):
    def add_reader(self, reader: ReaderPlugin):
        self._plugin_items.append(reader)

    def iter_readers(
        self, path: Path | list[Path], min_priority: int = 0
    ) -> Iterator[tuple[str, ReaderPlugin]]:
        for reader in self._plugin_items:
            if reader.priority < min_priority:
                continue
            try:
                out = reader.match_model_type(path)
            except Exception as e:
                _warn_failed_provider(reader, e)
            else:
                if out is None:
                    _LOGGER.debug("Reader %r did not match", reader)
                else:
                    yield out, reader

    def get(
        self,
        path: Path | list[Path],
        empty_ok: bool = False,
        min_priority: int = 0,
    ) -> list[ReaderPlugin]:
        matched: list[ReaderPlugin] = []
        for reader in self._plugin_items:
            if reader.priority < min_priority:
                continue
            try:
                out = reader.match_model_type(path)
            except Exception as e:
                _warn_failed_provider(reader, e)
            else:
                if out is None:
                    _LOGGER.debug("%r did not match", reader)
                else:
                    matched.append(reader)
        _LOGGER.debug("Matched readers: %r", matched)
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
    ) -> ReaderPlugin:
        """Pick a reader that match the inputs."""
        if plugin is not None:
            # if plugin is given, force to use it
            min_priority = -float("inf")
        return _pick_from_list(self.get(path, min_priority=min_priority), plugin)

    def run(
        self,
        path: Path | list[Path],
        *,
        plugin: str | None = None,
        min_priority: int = -float("inf"),
    ) -> WidgetDataModel:
        reader = self.pick(path, plugin=plugin, min_priority=min_priority)
        return reader.read(path)


class WriterProviderStore(ProviderStore["WriterPlugin"]):
    def add_writer(self, reader: WriterPlugin):
        self._plugin_items.append(reader)

    def get(
        self,
        model: WidgetDataModel,
        path: Path,
        empty_ok: bool = False,
        min_priority: int = 0,
    ) -> list[WriterPlugin]:
        matched: list[WriterPlugin] = []
        for writer in self._plugin_items:
            if writer.priority < min_priority:
                continue
            try:
                out = writer.match_input(model, path)
            except Exception as e:
                _warn_failed_provider(writer, e)
            else:
                if not out:
                    _LOGGER.debug("%r did not match", writer)
                else:
                    matched.append(writer)
        if not matched and not empty_ok:
            raise ValueError(f"No writer functions available for {model.type!r}")
        return matched

    def pick(
        self,
        model: WidgetDataModel,
        path: Path,
        plugin: str | None = None,
        min_priority: int = 0,
    ) -> WriterPlugin:
        """Pick a writer that match the inputs to write the model."""
        if plugin is not None:
            # if plugin is given, force to use it
            min_priority = -float("inf")
        return _pick_from_list(self.get(model, path, min_priority=min_priority), plugin)

    def run(
        self,
        model: WidgetDataModel,
        path: Path,
        *,
        plugin: str | None = None,
        min_priority: int = -float("inf"),
    ) -> None:
        writer = self.pick(model, path, plugin=plugin, min_priority=min_priority)
        return writer.write(model, path)


def _pick_by_priority(tuples: list[_S]) -> _S:
    return max(tuples, key=lambda x: x.priority)


def _pick_from_list(choices: list[_S], plugin: str | None) -> _S:
    if plugin is None:
        out = _pick_by_priority(choices)
    else:
        plugin_info = PluginInfo.from_str(plugin)
        for each in choices:
            if each.plugin == plugin_info:
                out = each
                break
        else:
            warnings.warn(
                f"Plugin {plugin} not found, using the default one.",
                UserWarning,
                stacklevel=2,
            )
            out = _pick_by_priority(choices)
    _LOGGER.debug("Picked: %r", out)
    return out


def _warn_failed_provider(plugin_obj, e: Exception):
    return _LOGGER.error(f"Error in {plugin_obj!r}: {e}")
