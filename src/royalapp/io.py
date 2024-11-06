from __future__ import annotations

from pathlib import Path
from typing import Callable, TypeVar, overload, NamedTuple
import warnings
from royalapp.types import WidgetDataModel, ReaderFunction, WriterFunction
from royalapp._utils import get_widget_data_model_variable

_ReaderProvider = Callable[["Path | list[Path]"], ReaderFunction]
_WriterProvider = Callable[[WidgetDataModel], WriterFunction]

_RP = TypeVar("_RP", bound=_ReaderProvider)
_WP = TypeVar("_WP", bound=_WriterProvider)


class ReaderProviderInfo(NamedTuple):
    provider: _ReaderProvider
    priority: int

    @property
    def plugin(self) -> str | None:
        if mod := getattr(self.provider, "__module__"):
            return mod
        return None


_READER_PROVIDERS: list[ReaderProviderInfo] = []
_WRITER_PROVIDERS: list[tuple[_WriterProvider, int]] = []


def get_readers(
    file_path: Path | list[Path], empty_ok: bool = False
) -> list[ReaderFunction]:
    """Get reader functions."""
    matched: list[tuple[ReaderFunction, int]] = []
    priority_max = -1
    for info in _READER_PROVIDERS:
        try:
            out = info.provider(file_path)
        except Exception as e:
            _warn_failed_provider(info.provider, e)
        else:
            if out:
                if callable(out):
                    matched.append((out, info.priority))
                    priority_max = max(priority_max, info.priority)
                else:
                    warnings.warn(
                        f"Reader provider {info.provider!r} returned {out!r}, which is "
                        "not callable."
                    )
    if not matched and not empty_ok:
        if isinstance(file_path, list):
            msg = [p.name for p in file_path]
        else:
            msg = file_path.name
        raise ValueError(f"No reader functions available for {msg!r}")
    return [fn for fn, pri in matched if pri == priority_max]


def get_writers(
    file_data: WidgetDataModel, empty_ok: bool = False
) -> list[WriterFunction]:
    """Get writer."""
    matched: list[tuple[WriterFunction, int]] = []
    priority_max = -1
    for provider, priority in _WRITER_PROVIDERS:
        try:
            out = provider(file_data)
        except Exception as e:
            _warn_failed_provider(provider, e)
        else:
            if out:
                if callable(out):
                    matched.append((out, priority))
                    priority_max = max(priority_max, priority)
                else:
                    warnings.warn(
                        f"Writer provider {provider!r} returned {out!r}, which is not"
                        "callable."
                    )
    if not matched and not empty_ok:
        raise ValueError(f"No writer functions available for {file_data.type!r}")
    return [fn for fn, pri in matched if pri == priority_max]


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
        _READER_PROVIDERS.append(ReaderProviderInfo(func, priority))
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
        _WRITER_PROVIDERS.append((TypedWriterProvider.try_convert(func), priority))
        return func

    return _inner if provider is None else _inner(provider)


def _check_priority(priority: int):
    if isinstance(priority, int) or hasattr(priority, "__int__"):
        return int(priority)
    raise TypeError(f"Priority must be an integer, not {type(priority)}.")


class TypedWriterProvider:
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
            return TypedWriterProvider(func, arg)
        return func
