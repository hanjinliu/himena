from __future__ import annotations

from typing import Annotated, Callable, TypeVar, get_origin, get_args, Any, overload
import inspect
from himena.types import GuiConfiguration


def _is_annotated(annotation: Any) -> bool:
    """Check if a type hint is an Annotated type."""
    return get_origin(annotation) is Annotated


def _split_annotated_type(annotation) -> tuple[Any, dict]:
    """Split an Annotated type into its base type and options dict."""
    if not _is_annotated(annotation):
        raise TypeError("Type hint must be an 'Annotated' type.")

    typ, *meta = get_args(annotation)
    all_meta = {}
    for m in meta:
        if not isinstance(m, dict):
            raise TypeError(
                "Invalid Annotated format for magicgui. Arguments must be a dict"
            )
        all_meta.update(m)

    return typ, all_meta


_F = TypeVar("_F", bound=Callable)


@overload
def configure_gui(
    f: _F,
    *,
    title: str | None = None,
    auto_close: bool = True,
    show_parameter_labels: bool = True,
    **kwargs,
) -> _F: ...
@overload
def configure_gui(
    *,
    title: str | None = None,
    auto_close: bool = True,
    show_parameter_labels: bool = True,
    **kwargs,
) -> Callable[[_F], _F]: ...


def configure_gui(
    f=None,
    *,
    title: str | None = None,
    auto_close: bool = True,
    show_parameter_labels: bool = True,
    **kwargs,
):
    """Configure the GUI options for each parameter of a function.

    The usage is the same as `magicgui`'s `@magicgui` decorator.

    >>> @configure_gui(a={"label": "A", "widget_type": "FloatSlider"})
    ... def my_func(a: float):
    ...     pass
    """

    def _inner(f):
        sig = inspect.signature(f)
        new_params = sig.parameters.copy()
        for k, v in kwargs.items():
            if k not in sig.parameters:
                raise TypeError(f"{k!r} is not a valid parameter for {f!r}.")
            param = sig.parameters[k]
            if not _is_annotated(param.annotation):
                annot = _prioritize_choices(param.annotation, v)
                param = param.replace(annotation=Annotated[annot, v])
            else:
                typ, meta = _split_annotated_type(param.annotation)
                meta.update(v)
                typ = _prioritize_choices(typ, meta)
                param = param.replace(annotation=Annotated[typ, meta])
            new_params[k] = param
        sig = sig.replace(parameters=list(new_params.values()))
        f.__signature__ = sig
        f.__annotations__ = {k: v.annotation for k, v in sig.parameters.items()}
        f.__himena_gui_config__ = GuiConfiguration(
            title=title,
            auto_close=auto_close,
            show_parameter_labels=show_parameter_labels,
        )
        return f

    return _inner if f is None else _inner(f)


def _prioritize_choices(annotation, options: dict[str, Any]):
    if "choices" in options:
        typ = Any
    else:
        typ = annotation
    return typ
