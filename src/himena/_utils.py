from __future__ import annotations
from typing import (
    Callable,
    Any,
    Generic,
    Hashable,
    Iterable,
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

from himena.types import (
    ParametricWidgetProtocol,
    WidgetDataModel,
    Parametric,
    ModelTrack,
    GuiConfiguration,
)
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


@lru_cache
def get_widget_class_id(cls: type) -> str:
    """Get the widget ID from the class.

    Widget ID is always determined by the register_widget_class decorator. This ID is
    used during the application to identify the widget class.
    """
    import importlib

    if _widget_id := getattr(cls, "__himena_widget_id__", None):
        if not isinstance(_widget_id, str):
            raise TypeError(f"Widget ID must be a string, got {type(_widget_id)}")
        return _widget_id

    name = f"{cls.__module__}.{cls.__name__}"
    # look for simpler import path
    submods = cls.__module__.split(".")
    for i in range(1, len(submods)):
        mod_name = ".".join(submods[:i])
        try:
            mod = importlib.import_module(mod_name)
            if getattr(mod, cls.__name__, None) is cls:
                name = f"{mod_name}.{cls.__name__}"
                break
        except Exception:
            pass

    # replace the first "." with ":" to make names consistent
    name = name.replace(".", ":", 1)
    return name


def get_display_name(cls: type) -> str:
    if title := getattr(cls, "__himena_display_name__", None):
        if not isinstance(title, str):
            raise TypeError(f"Display name must be a string, got {type(title)}")
    else:
        title = cls.__name__
    name = get_widget_class_id(cls)

    return f"{title}\n({name})"


_T = TypeVar("_T", bound=Hashable)


class OrderedSet(MutableSet[_T]):
    def __init__(self, iterable: Iterable[_T] = ()):
        self._dict: dict[_T, None] = dict.fromkeys(iterable)

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

    def update(self, other: Iterable[_T]) -> None:
        for value in other:
            self.add(value)


def _is_widget_data_model(a):
    return WidgetDataModel in (get_origin(a), a)


def _is_subwindow(a):
    from himena.widgets._wrapper import SubWindow

    return SubWindow in (get_origin(a), a)


def _is_parametric(a):
    return a is Parametric


def make_function_callback(
    f: _F,
    command_id: str,
    title: str | None = None,
) -> _F:
    from himena.widgets._wrapper import SubWindow

    try:
        sig = inspect.signature(f)
    except Exception:
        warnings.warn(f"Failed to get signature of {f!r}")
        return f

    f_annot = f.__annotations__
    keys_model: list[str] = []
    keys_subwindow: list[str] = []
    for key, param in sig.parameters.items():
        if _is_widget_data_model(param.annotation):
            keys_model.append(key)
        elif _is_subwindow(param.annotation):
            keys_subwindow.append(key)

    for key in keys_model:
        f_annot[key] = WidgetDataModel

    if _is_widget_data_model(sig.return_annotation):
        f_annot["return"] = WidgetDataModel
    elif _is_subwindow(sig.return_annotation):
        f_annot["return"] = SubWindow
    elif _is_parametric(sig.return_annotation):
        f_annot["return"] = Parametric
    elif sig.return_annotation is ParametricWidgetProtocol:
        f_annot["return"] = ParametricWidgetProtocol
    else:
        return f

    if len(keys_model) + len(keys_subwindow) == 0 and f_annot.get("return") not in {
        Parametric,
        ParametricWidgetProtocol,
    }:
        return f

    @wraps(f)
    def _new_f(*args, **kwargs):
        bound = sig.bind(*args, **kwargs)
        out = f(*args, **kwargs)
        originals = []
        for key in keys_model + keys_subwindow:
            input_ = bound.arguments[key]
            if isinstance(input_, WidgetDataModel):
                input_method = input_.method
            elif isinstance(input_, SubWindow):
                input_method = input_.to_model().method
            else:
                input_method = None
            if input_method is None:
                method = ProgramaticMethod()
            else:
                method = input_method
            originals.append(method)
        if isinstance(out, WidgetDataModel):
            if len(originals) > 0:
                out.method = ConverterMethod(originals=originals, command_id=command_id)
        elif f_annot.get("return") in (Parametric, ParametricWidgetProtocol):
            out.__himena_model_track__ = ModelTrack(
                sources=originals, command_id=command_id
            )
            if title is not None:
                cfg = getattr(out, _HIMENA_GUI_CONFIG, GuiConfiguration())
                cfg.title = title
                setattr(out, _HIMENA_GUI_CONFIG, cfg)
        return out

    return _new_f


_HIMENA_GUI_CONFIG = "__himena_gui_config__"


def get_gui_config(fn) -> dict[str, Any]:
    if isinstance(
        config := getattr(fn, _HIMENA_GUI_CONFIG, None),
        GuiConfiguration,
    ):
        out = config.model_dump()
    else:
        out = {}
    if out.get("title") is None:
        if hasattr(fn, "__name__"):
            out["title"] = fn.__name__
        else:
            out["title"] = str(fn)
    return out


def import_object(full_name: str) -> Any:
    """Import object by a period-separated full name or the widget ID."""
    import importlib
    from himena.plugins import get_widget_class

    if obj := get_widget_class(full_name):
        return obj
    mod_name, func_name = full_name.replace(":", ".", 1).rsplit(".", 1)
    mod = importlib.import_module(mod_name)
    obj = getattr(mod, func_name)
    return obj


def add_title_suffix(title: str) -> str:
    """Add [n] suffix to the title."""
    if "." in title:
        stem, ext = title.rsplit(".", 1)
        ext = f".{ext}"
    else:
        stem = title
        ext = ""
    if (
        (last_part := stem.rsplit(" ", 1)[-1]).startswith("[")
        and last_part.endswith("]")
        and last_part[1:-1].isdigit()
    ):
        nth = int(last_part[1:-1])
        stem = stem.rsplit(" ", 1)[0] + f" [{nth + 1}]"
    else:
        stem = stem + " [1]"
    return stem + ext


class UndoRedoStack(Generic[_T]):
    """A simple undo/redo stack to store the history."""

    def __init__(self, size: int = 10):
        self._stack_undo: list[_T] = []
        self._stack_redo: list[_T] = []
        self._size = size

    def push(self, value: _T):
        """Push a new value."""
        self._stack_undo.append(value)
        self._stack_redo.clear()
        if len(self._stack_undo) > self._size:
            self._stack_undo.pop(0)

    def undo(self) -> _T | None:
        """Undo and return the value. None if empty."""
        if len(self._stack_undo) == 0:
            return None
        value = self._stack_undo.pop()
        self._stack_redo.append(value)
        return value

    def redo(self) -> _T | None:
        """Redo and return the value. None if empty."""
        if len(self._stack_redo) == 0:
            return None
        value = self._stack_redo.pop()
        self._stack_undo.append(value)
        return value

    def undoable(self) -> bool:
        """If undo is possible."""
        return len(self._stack_undo) > 0

    def redoable(self) -> bool:
        """If redo is possible."""
        return len(self._stack_redo) > 0
