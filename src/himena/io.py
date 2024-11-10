from __future__ import annotations

from pathlib import Path
from logging import getLogger
from typing import Callable, TypeVar, overload, NamedTuple
import warnings
from himena.types import WidgetDataModel, ReaderFunction, WriterFunction
from himena._utils import get_widget_data_model_variable

_LOGGER = getLogger(__name__)
_ReaderProvider = Callable[["Path | list[Path]"], ReaderFunction]
_WriterProvider = Callable[[WidgetDataModel], WriterFunction]

_RP = TypeVar("_RP", bound=_ReaderProvider)
_WP = TypeVar("_WP", bound=_WriterProvider)


class PluginInfo(NamedTuple):
    module: str
    name: str

    def to_str(self) -> str:
        """Return the string representation of the plugin."""
        return f"{self.module}.{self.name}"


def _plugin_info_from_func(func: Callable) -> PluginInfo | None:
    if hasattr(func, "__module__"):
        module = func.__module__
        if hasattr(func, "__qualname__"):
            qual = func.__qualname__
            if not qual.isidentifier():
                return None
            return PluginInfo(module, qual)
        if hasattr(func, "__name__"):
            return PluginInfo(module, func.__name__)
    return None


class ReaderProviderTuple(NamedTuple):
    provider: _ReaderProvider
    priority: int
    plugin: PluginInfo | None = None


class WriterProviderTuple(NamedTuple):
    provider: _WriterProvider
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


_T = TypeVar("_T", ReaderTuple, WriterTuple)


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


@overload
def register_reader_provider(provider: _RP, *, priority: int = 0) -> _RP: ...
@overload
def register_reader_provider(*, priority: int = 0) -> Callable[[_RP], _RP]: ...


def register_reader_provider(provider=None, priority=0):
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
    _check_priority(priority)

    def _inner(func):
        if not callable(func):
            raise ValueError("Provider must be callable.")
        plugin = _plugin_info_from_func(func)
        _READER_PROVIDERS.append(ReaderProviderTuple(func, priority, plugin))
        return func

    return _inner if provider is None else _inner(provider)


@overload
def register_writer_provider(provider: _WP, *, priority: int = 0) -> _WP: ...
@overload
def register_writer_provider(*, priority: int = 0) -> _WP: ...


def register_writer_provider(provider=None, priority=0):
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
    _check_priority(priority)

    def _inner(func):
        if not callable(func):
            raise ValueError("Provider must be callable.")
        plugin = _plugin_info_from_func(func)
        tup = WriterProviderTuple(TypedProvider.try_convert(func), priority, plugin)
        _WRITER_PROVIDERS.append(tup)
        return func

    return _inner if provider is None else _inner(provider)


def _check_priority(priority: int):
    if isinstance(priority, int) or hasattr(priority, "__int__"):
        return int(priority)
    raise TypeError(f"Priority must be an integer, not {type(priority)}.")


class TypedProvider:
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
            return TypedProvider(func, arg)
        return func
