from __future__ import annotations
from typing import (
    Callable,
    Any,
    Hashable,
    Iterator,
    MutableSet,
    TypeVar,
    TYPE_CHECKING,
    overload,
    get_origin,
)
import inspect
from functools import wraps
import warnings
from himena.types import WidgetDataModel, Parametric
from himena._descriptors import ProgramaticMethod, ConverterMethod

if TYPE_CHECKING:
    _F = TypeVar("_F", bound=Callable)

    @overload
    def lru_cache(maxsize: int = 128, typed: bool = False) -> Callable[[_F], _F]: ...
    @overload
    def lru_cache(f: _F) -> _F: ...
else:
    from functools import lru_cache  # noqa: F401


def get_widget_data_model_variable(func: Callable) -> type | None:
    annots = [v for k, v in func.__annotations__.items() if k != "return"]
    if len(annots) != 1:
        return None
    annot = annots[0]
    if not (hasattr(annot, "__origin__") and hasattr(annot, "__args__")):
        return None
    if annot.__origin__ is not WidgetDataModel:
        return None
    if len(annot.__args__) != 1:
        return None
    return annot.__args__[0]


def has_widget_data_model_argument(func: Callable) -> bool:
    """If true, the function has a WidgetDataModel type hint."""
    for k, v in func.__annotations__.items():
        if k == "return":
            continue
        if v is WidgetDataModel:
            return True
        if hasattr(v, "__origin__") and hasattr(v, "__args__"):
            if v.__origin__ is WidgetDataModel:
                return True
    return False


_T = TypeVar("_T", bound=Hashable)


class OrderedSet(MutableSet[_T]):
    def __init__(self):
        self._dict: dict[_T, None] = {}

    def __contains__(self, other) -> bool:
        return other in self._dict

    def __iter__(self) -> Iterator[_T]:
        yield from self._dict

    def __len__(self) -> int:
        return len(self._dict)

    def add(self, value: _T) -> None:
        self._dict[value] = None

    def discard(self, value: _T) -> None:
        self._dict.pop(value, None)


def _is_widget_data_model(a):
    return WidgetDataModel in (get_origin(a), a)


def _is_parametric(a):
    return Parametric in (get_origin(a), a)


def make_function_callback(
    f: _F,
    command_id: str,
    preview: bool = False,
) -> _F:
    try:
        sig = inspect.signature(f)
    except Exception:
        warnings.warn(f"Failed to get signature of {f!r}")
        return f

    keys_model: list[str] = []
    for key, param in sig.parameters.items():
        if _is_widget_data_model(param.annotation):
            keys_model.append(key)

    for key in keys_model:
        f.__annotations__[key] = WidgetDataModel

    if _is_widget_data_model(sig.return_annotation):
        f.__annotations__["return"] = WidgetDataModel
    elif _is_parametric(sig.return_annotation):
        f.__annotations__["return"] = Parametric
    else:
        return f

    if len(keys_model) == 0 and f.__annotations__["return"] is not Parametric:
        return f

    @wraps(f)
    def _new_f(*args, **kwargs):
        bound = sig.bind(*args, **kwargs)
        out = f(*args, **kwargs)
        originals = []
        for key in keys_model:
            input_ = bound.arguments[key]
            if isinstance(input_, WidgetDataModel):
                if input_.method is None:
                    method = ProgramaticMethod()
                else:
                    method = input_.method
                originals.append(method)
        if isinstance(out, WidgetDataModel):
            if len(originals) > 0:
                out.method = ConverterMethod(originals=originals, command_id=command_id)
        elif callable(out) and f.__annotations__["return"] is Parametric:
            out = Parametric(
                out,
                sources=originals,
                command_id=command_id,
                preview=preview,
            )
        return out

    return _new_f


def make_opener_callback(f: _F) -> _F:
    @wraps(f)
    def _new_f(*args, **kwargs):
        out = f(*args, **kwargs)
        if not isinstance(out, WidgetDataModel):
            raise RuntimeError(f"Expected WidgetDataModel, got {out!r}")
        return out

    return Parametric(_new_f)


def import_object(full_name: str) -> Any:
    """Import object by a period-separated full name."""
    import importlib

    mod_name, func_name = full_name.rsplit(".", 1)
    mod = importlib.import_module(mod_name)
    obj = getattr(mod, func_name)
    return obj


def add_title_suffix(title: str) -> str:
    """Add [n] suffix to the title."""
    if (
        (last_part := title.rsplit(" ", 1)[-1]).startswith("[")
        and last_part.endswith("]")
        and last_part[1:-1].isdigit()
    ):
        nth = int(last_part[1:-1])
        title = title.rsplit(" ", 1)[0] + f" [{nth + 1}]"
    else:
        title = title + " [1]"
    return title
