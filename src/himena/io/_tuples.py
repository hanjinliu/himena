from __future__ import annotations

from pathlib import Path
from typing import NamedTuple

from himena.types import (
    WidgetDataModel,
    ReaderFunction,
    WriterFunction,
    ReaderProvider,
    WriterProvider,
)


class PluginInfo(NamedTuple):
    """Tuple that describes a plugin function."""

    module: str
    name: str

    def to_str(self) -> str:
        """Return the string representation of the plugin."""
        return f"{self.module}.{self.name}"

    @classmethod
    def from_str(cls, s: str) -> PluginInfo:
        """Create a PluginInfo from a string."""
        mod_name, func_name = s.rsplit(".", 1)
        return PluginInfo(module=mod_name, name=func_name)


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
