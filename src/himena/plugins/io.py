from __future__ import annotations

from functools import wraps
from pathlib import Path
from typing import Any, Callable, ForwardRef, TypeVar, overload
from himena.types import WidgetDataModel, ReaderProvider, WriterProvider
from himena.utils.misc import PluginInfo
from himena._providers import ReaderProviderStore, WriterProviderStore
from himena._utils import get_widget_data_model_type_arg

_RP = TypeVar("_RP", bound=ReaderProvider)
_WP = TypeVar("_WP", bound=WriterProvider)


def _plugin_info_from_func(func: Callable) -> PluginInfo | None:
    if hasattr(func, "__module__"):
        module = func.__module__
        if module == "__main__" or "<" in module:
            # this plugin will never be available. Skip it.
            return None
        if hasattr(func, "__qualname__"):
            qual = func.__qualname__
            if not qual.isidentifier():
                return None
            return PluginInfo(module, qual)
        if hasattr(func, "__name__"):
            return PluginInfo(module, func.__name__)
    return None


class _IOPluginBase:
    __qualname__: str
    __module__: str
    __name__: str

    def __init__(
        self,
        func: Callable,
        matcher: Callable | None = None,
        *,
        priority: int = 100,
    ):
        self._priority = _check_priority(priority)
        self._func = func
        self._matcher = matcher
        self._plugin = _plugin_info_from_func(func)
        self.__name__ = str(func)  # default value
        wraps(func)(self)

    @property
    def priority(self) -> int:
        return self._priority

    @property
    def plugin(self) -> PluginInfo | None:
        return self._plugin

    @property
    def plugin_str(self) -> str | None:
        return self._plugin.to_str() if self._plugin else None

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {self.plugin_str}>"


class ReaderPlugin(_IOPluginBase):
    def __init__(
        self,
        reader: Callable[[Path | list[Path]], WidgetDataModel],
        matcher: Callable[[Path | list[Path]], bool] | None = None,
        *,
        priority: int = 100,
    ):
        super().__init__(reader, matcher, priority=priority)
        self._skip_if_list = False
        if hasattr(reader, "__annotations__"):
            annot_types = list(reader.__annotations__.values())
            if len(annot_types) == 1 and annot_types[0] in (
                Path,
                "Path",
                ForwardRef("Path"),
            ):
                self._skip_if_list = True

    def read(self, path: Path | list[Path]) -> WidgetDataModel:
        """Read file(s) and return a data model."""
        if isinstance(path, list):
            out = self._func([Path(p) for p in path])
        else:
            out = self._func(Path(path))
        if not isinstance(out, WidgetDataModel):
            raise TypeError(f"Reader plugin {self!r} did not return a WidgetDataModel.")
        return out

    __call__ = read

    def match_model_type(self, path: Path | list[Path]) -> str | None:
        """True if the reader can read the file."""
        if self._skip_if_list and isinstance(path, list):
            return None
        out = self._matcher(path)
        if out is None or isinstance(out, str):
            return out
        raise TypeError(f"Matcher {self._matcher!r} did not return a string.")

    def mark_matcher(self, matcher: Callable[[Path | list[Path]], str | None]):
        """Mark a function as a matcher."""
        self._matcher = matcher
        return matcher

    def read_and_update_source(self, source: Path | list[Path]) -> WidgetDataModel:
        """Update workflow to a local-reader method if it is not set."""
        model = self.read(source)
        if len(model.workflow) == 0:
            model = model._with_source(source=source, plugin=self.plugin)
        return model


class WriterPlugin(_IOPluginBase):
    def __init__(
        self,
        writer: Callable[[WidgetDataModel, Path], Any],
        matcher: Callable[[Path | list[Path]], bool] | None = None,
        *,
        priority: int = 100,
    ):
        super().__init__(writer, matcher, priority=priority)
        if arg := get_widget_data_model_type_arg(writer):
            self._value_type_filter = arg
        else:
            self._value_type_filter = None

    def write(self, model: WidgetDataModel, path: Path) -> None:
        return self._func(model, path)

    __call__ = write

    def match_input(self, model: WidgetDataModel, path: Path) -> bool:
        if self._value_type_filter is not None and not isinstance(
            model.value, self._value_type_filter
        ):
            return False
        return self._matcher(model, path)

    def mark_matcher(
        self, matcher: Callable[[Path, WidgetDataModel], bool]
    ) -> WriterPlugin:
        self._matcher = matcher
        return self


@overload
def register_reader_plugin(
    reader: Callable[[Path | list[Path]], WidgetDataModel],
    *,
    priority: int = 100,
    function_id: str | None = None,
) -> ReaderPlugin: ...
@overload
def register_reader_plugin(
    *,
    priority: int = 100,
    function_id: str | None = None,
) -> Callable[[Callable[[Path | list[Path]], WidgetDataModel]], ReaderPlugin]: ...


def register_reader_plugin(reader=None, *, priority=100, function_id=None):
    def _inner(func):
        if not callable(func):
            raise ValueError("Provider must be callable.")
        ins = ReaderProviderStore().instance()

        reader_plugin = ReaderPlugin(func, priority=priority)
        ins.add_reader(reader_plugin)
        return reader_plugin

    return _inner if reader is None else _inner(reader)


@overload
def register_writer_plugin(
    writer: Callable[[WidgetDataModel, Path], Any],
    *,
    priority: int = 100,
    function_id: str | None = None,
) -> WriterPlugin: ...
@overload
def register_writer_plugin(
    *,
    priority: int = 100,
    function_id: str | None = None,
) -> Callable[[Callable[[WidgetDataModel, Path], Any]], WriterPlugin]: ...


def register_writer_plugin(writer=None, *, priority=100, function_id=None):
    def _inner(func):
        if not callable(func):
            raise ValueError("Provider must be callable.")
        ins = WriterProviderStore().instance()

        writer_plugin = WriterPlugin(func, priority=priority)
        ins.add_writer(writer_plugin)
        return writer_plugin

    return _inner if writer is None else _inner(writer)


def _check_priority(priority: int):
    if isinstance(priority, int) or hasattr(priority, "__int__"):
        return int(priority)
    raise TypeError(f"Priority must be an integer, not {type(priority)}.")
