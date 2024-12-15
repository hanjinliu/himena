from __future__ import annotations

from typing import (
    Annotated,
    Callable,
    Literal,
    TypeVar,
    get_origin,
    get_args,
    Any,
    overload,
)
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
    preview: bool = False,
    auto_close: bool = True,
    show_parameter_labels: bool = True,
    gui_options: dict[str, Any] | None = None,
    run_async: bool = False,
    result_as: Literal["window", "below", "right"] = "window",
    **kwargs,
) -> _F: ...
@overload
def configure_gui(
    *,
    title: str | None = None,
    preview: bool = False,
    auto_close: bool = True,
    show_parameter_labels: bool = True,
    gui_options: dict[str, Any] | None = None,
    run_async: bool = False,
    result_as: Literal["window", "below", "right"] = "window",
    **kwargs,
) -> Callable[[_F], _F]: ...


def configure_gui(
    f=None,
    *,
    title: str | None = None,
    preview: bool = False,
    auto_close: bool = True,
    show_parameter_labels: bool = True,
    gui_options: dict[str, Any] | None = None,
    run_async: bool = False,
    result_as: Literal["window", "below", "right"] = "window",
    **kwargs,
):
    """Configure the parametric GUI.

    This decorator sets the configuration options for the parametric GUI window.

    >>> @configure_gui(a={"label": "A", "widget_type": "FloatSlider"})
    ... def my_func(a: float):
    ...     pass

    Parameters
    ----------
    title : str, optional
        The title of the parametric GUI window. If not provided, this title will be
        determined by the action title where this function is returned.
    preview : bool, default False
        If true, a preview toggle switch will be added to the GUI window. When the
        switch is on, the function will be called and the result will be displayed. Note
        that `configure_gui` does not consider whether the preview is a heavy operation.
    auto_close : bool, default True
        If true, the parametric GUI window will be closed automatically after the
        function is executed.
    show_parameter_labels : bool, default True
        If true, the parameter names will be shown in the GUI window.
    gui_options : dict, optional
        Additional GUI options to be passed to the `magicgui` decorator. Keys can also
        be passed as variable keyword arguments **kwargs.
    run_async : bool, default False
        If true, the function will be executed asynchronously. Note that if the function
        updates the GUI, running it asynchronously may cause issues.
    """
    kwargs = dict(**kwargs, **(gui_options or {}))

    def _inner(f):
        sig = inspect.signature(f)
        new_params = sig.parameters.copy()
        if var_kwargs_name := _get_var_kwargs_name(sig):
            new_params.pop(var_kwargs_name)

        for k, v in kwargs.items():
            if k not in new_params:
                if var_kwargs_name is None:
                    raise TypeError(f"{k!r} is not a valid parameter for {f!r}.")
                # This allows using **kwargs in the target function so that magicgui
                # widget can be created for a variable number of parameters.
                param = inspect.Parameter(name=k, kind=inspect.Parameter.KEYWORD_ONLY)
            else:
                param = sig.parameters[k]
            # unwrap Annotated types
            if not _is_annotated(param.annotation):
                annot = _prioritize_choices(param.annotation, v)
                param = param.replace(annotation=Annotated[annot, v])
            else:
                typ, meta = _split_annotated_type(param.annotation)
                meta.update(v)
                typ = _prioritize_choices(typ, meta)
                param = param.replace(annotation=Annotated[typ, meta])
            new_params[k] = param
        # update the signature with the normalize one
        sig = sig.replace(parameters=list(new_params.values()))
        f.__signature__ = sig
        f.__annotations__ = {k: v.annotation for k, v in sig.parameters.items()}
        if sig.return_annotation is not inspect.Parameter.empty:
            f.__annotations__["return"] = sig.return_annotation

        f.__himena_gui_config__ = GuiConfiguration(
            title=title,
            preview=preview,
            auto_close=auto_close,
            show_parameter_labels=show_parameter_labels,
            run_async=run_async,
            result_as=result_as,
        )
        return f

    return _inner if f is None else _inner(f)


def _prioritize_choices(annotation, options: dict[str, Any]):
    if "choices" in options:
        typ = Any
    else:
        typ = annotation
    return typ


def _get_var_kwargs_name(sig: inspect.Signature) -> str | None:
    """Get the name of the **kwargs parameter."""
    for p in sig.parameters.values():
        if p.kind == inspect.Parameter.VAR_KEYWORD:
            return p.name
    return None
