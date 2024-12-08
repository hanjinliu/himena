from __future__ import annotations

from pathlib import Path
from typing import Callable, ForwardRef, TypeVar, overload
from himena.types import WidgetDataModel, ReaderProvider, WriterProvider
from himena import _providers
from himena._utils import get_widget_data_model_variable

_RP = TypeVar("_RP", bound=ReaderProvider)
_WP = TypeVar("_WP", bound=WriterProvider)


def _plugin_info_from_func(func: Callable) -> _providers.PluginInfo | None:
    if hasattr(func, "__module__"):
        module = func.__module__
        if module == "__main__" or "<" in module:
            # this plugin will never be available. Skip it.
            return None
        if hasattr(func, "__qualname__"):
            qual = func.__qualname__
            if not qual.isidentifier():
                return None
            return _providers.PluginInfo(module, qual)
        if hasattr(func, "__name__"):
            return _providers.PluginInfo(module, func.__name__)
    return None


@overload
def register_reader_provider(
    provider: _RP,
    *,
    priority: int = 100,
    function_id: str | None = None,
) -> _RP: ...
@overload
def register_reader_provider(
    *,
    priority: int = 100,
    function_id: str | None = None,
) -> Callable[[_RP], _RP]: ...


def register_reader_provider(provider=None, *, priority=100, function_id=None):
    """
    Register reader provider function.

    This function should return a reader function for the given file path, or None if
    your plugin does not support the file type.

    >>> @register_reader_provider
    ... def my_reader_provider(path):
    ...     if Path(path).suffix != ".txt":
    ...         return None
    ...     # this is the reader function
    ...     def _read_text(path):
    ...         with open(path) as f:
    ...             return WidgetDataModel(value=f.read(), type="text", source=path)
    ...     return _read_text
    """
    _check_priority(priority)

    def _inner(func):
        if not callable(func):
            raise ValueError("Provider must be callable.")
        plugin = _plugin_info_from_func(func)
        ins = _providers.ReaderProviderStore().instance()

        if hasattr(func, "__annotations__"):
            annot_types = list(func.__annotations__.values())
            _allowed = (Path, "Path", ForwardRef("Path"))
            if len(annot_types) == 1 and annot_types[0] in _allowed:
                func = _skip_if_list_of_paths(func)

        ins.add(func, priority, plugin)
        return func

    return _inner if provider is None else _inner(provider)


def _skip_if_list_of_paths(func: Callable) -> Callable:
    def _new(*args, **kwargs):
        if isinstance(args[0], list):
            return None
        return func(*args, **kwargs)

    return _new


@overload
def register_writer_provider(provider: _WP, *, priority: int = 100) -> _WP: ...
@overload
def register_writer_provider(*, priority: int = 100) -> _WP: ...


def register_writer_provider(provider=None, priority=100):
    """
    Register writer provider function.

    This function should return a writer function for the given data model, or None if
    your plugin does not support the data type.

    >>> @register_writer_provider
    ... def my_writer_provider(model: WidgetDataModel):
    ...     if not isinstance(model.value, str) or model.source.suffix != ".txt":
    ...         return None
    ...     # this is the writer function
    ...     def _write_text(model: WidgetDataModel, path):
    ...         with open(path, "w") as f:
    ...             f.write(model.value)
    ...     return _write_text
    """
    _check_priority(priority)

    def _inner(func):
        if not callable(func):
            raise ValueError("Provider must be callable.")
        plugin = _plugin_info_from_func(func)
        ins = _providers.WriterProviderStore().instance()
        ins.add(TypedProvider.try_convert(func), priority, plugin)
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
