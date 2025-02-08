from __future__ import annotations

from concurrent.futures import Future
import timeit
from typing import (
    Callable,
    Any,
    TypeVar,
    get_origin,
)
import inspect
from functools import wraps
import warnings
from textwrap import dedent
from cmap import Colormap, Color

from himena.consts import StandardType
from himena.types import (
    FutureInfo,
    ParametricWidgetProtocol,
    WidgetDataModel,
    Parametric,
    ModelTrack,
    GuiConfiguration,
)
from himena.utils.misc import lru_cache
from himena.workflow import (
    CommandExecution,
    ModelParameter,
    parse_parameter,
    WindowParameter,
)
from himena.workflow import Workflow

_F = TypeVar("_F", bound=Callable)


def _get_type_arg(func: Callable, target: type) -> type | None:
    annots = [v for k, v in func.__annotations__.items() if k != "return"]
    if len(annots) != 1:
        return None
    annot = annots[0]
    if not (hasattr(annot, "__origin__") and hasattr(annot, "__args__")):
        return None
    if annot.__origin__ is not target:
        return None
    if len(annot.__args__) != 1:
        return None
    return annot.__args__[0]


def get_widget_data_model_type_arg(func: Callable) -> type | None:
    return _get_type_arg(func, WidgetDataModel)


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


def get_subwindow_type_arg(func: Callable) -> type | None:
    from himena.widgets import SubWindow

    return _get_type_arg(func, SubWindow)


def get_user_context(widget: Any) -> Any:
    """Get the user context from the widget."""
    if user_context := getattr(widget, "user_context", None):
        return user_context()
    return None


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


def get_display_name(cls: type, sep: str = "\n", class_id: bool = True) -> str:
    if title := getattr(cls, "__himena_display_name__", None):
        if not isinstance(title, str):
            raise TypeError(f"Display name must be a string, got {type(title)}")
    else:
        title = cls.__name__
    name = get_widget_class_id(cls)
    if class_id:
        return f"{title}{sep}({name})"
    else:
        return title


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
    run_async: bool = False,
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

    is_parametric = f_annot.get("return") in (Parametric, ParametricWidgetProtocol)

    @wraps(f)
    def _new_f(*args, **kwargs):
        bound = sig.bind(*args, **kwargs)
        _time_before = timeit.default_timer()
        out = f(*args, **kwargs)
        contexts = []
        workflows = []

        for key, input_ in bound.arguments.items():
            input_param, wf = parse_parameter(key, input_)
            if isinstance(input_param, (ModelParameter, WindowParameter)):
                contexts.append(input_param)
                workflows.append(wf)
        workflow = Workflow.concat(workflows)
        if isinstance(out, WidgetDataModel):
            out.workflow = out.workflow.with_step(
                CommandExecution(
                    contexts=contexts,
                    command_id=command_id,
                    execution_time=timeit.default_timer() - _time_before,
                )
            )
        elif is_parametric:
            ModelTrack(
                contexts=contexts,
                command_id=command_id,
                workflow=workflow,
                time_start=_time_before,
            ).set(out)
            if title is not None:
                cfg = GuiConfiguration.get(out) or GuiConfiguration()
                cfg.title = title
                cfg.run_async = run_async
                cfg.set(out)
        return out

    if run_async and not is_parametric:
        _new_f = _wrap_future(_new_f)
    return _new_f


def _wrap_future(f):
    from himena.widgets import current_instance

    return_annot = f.__annotations__.get("return")

    @wraps(f)
    def _f(*args, **kwargs):
        ins = current_instance()
        future = ins._executor.submit(f, *args, **kwargs)
        FutureInfo(return_annot).set(future)
        return future

    _f.__annotations__["return"] = Future
    return _f


def get_gui_config(fn) -> dict[str, Any]:
    if isinstance(config := GuiConfiguration.get(fn), GuiConfiguration):
        out = config.asdict()
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


def unwrap_lazy_model(model: WidgetDataModel) -> WidgetDataModel:
    """Unwrap the lazy object if possible."""

    if model.type != StandardType.LAZY:
        raise ValueError(f"Expected a lazy object, got type {model.type}")
    if not callable(val := model.value):
        raise ValueError(
            f"Expected a callable as the value of the WidgetDataModel, got {type(val)}"
        )
    out = val()
    if not isinstance(out, WidgetDataModel):
        raise ValueError(
            f"Expected a WidgetDataModel as the return value, got {type(out)}"
        )
    return out


def to_color_or_colormap(value) -> Color | Colormap:
    if isinstance(value, (Color, Colormap)):
        return value
    if isinstance(value, str) and value.startswith("#"):
        value = Color(value)
    elif isinstance(value, dict):
        value = Colormap(value)
    else:
        try:
            value = Colormap(value)
        except Exception:
            value = Color(value)
    return value


def doc_to_whats_this(doc: str):
    lines = doc.splitlines()
    first_line = lines[0]
    others = "\n".join(lines[1:])
    doc_dedent = dedent(first_line) + "\n" + dedent(others)
    return doc_dedent
