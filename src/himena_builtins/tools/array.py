from typing import Any, Literal, TypeVar
import operator as _op
import numpy as np
from himena.data_wrappers._array import wrap_array
from himena._descriptors import NoNeedToSave
from himena.plugins import register_function, configure_gui, configure_submenu
from himena.types import Parametric, WidgetDataModel
from himena.consts import StandardType, MenuId
from himena.standards.model_meta import ArrayMeta, ImageMeta, DimAxis
from himena.widgets import set_status_tip, SubWindow

configure_submenu(MenuId.TOOLS_ARRAY, group="20_builtins", order=5)


@register_function(
    types=StandardType.ARRAY,
    menus=[MenuId.TOOLS_ARRAY],
    command_id="builtins:array:duplicate-slice",
    keybindings=["Ctrl+Shift+D"],
)
def duplicate_this_slice(model: WidgetDataModel) -> Parametric:
    """Duplicate the slice of the array."""
    from himena.data_wrappers import wrap_array

    if not isinstance(meta := model.metadata, ArrayMeta):
        raise TypeError(
            "Widget does not have ArrayMeta thus cannot determine the slice indices."
        )

    def _get_indices(*_) -> "tuple[int | None, ...]":
        if (indices := meta.current_indices) is None:
            raise ValueError("The `current_indices` attribute is not set.")
        return indices

    @configure_gui(indices={"bind": _get_indices})
    def run_duplicate_this_slice(indices) -> WidgetDataModel:
        arr = wrap_array(model.value)
        arr_sliced = arr.get_slice(
            tuple(slice(None) if i is None else i for i in indices)
        )
        if isinstance(meta := model.metadata, ArrayMeta):
            update: dict[str, Any] = {"current_indices": ()}
            if isinstance(meta, ImageMeta):
                update["axes"] = meta.axes[-2:] if meta.axes is not None else None
                update["channel_axis"] = None
                # if the input image is colored, inherit the colormap
                if meta.channel_axis is not None:
                    update["channels"] = [meta.channels[indices[meta.channel_axis]]]
                else:
                    update["channels"] = None
            meta_sliced = meta.model_copy(update=update)
        else:
            meta_sliced = ArrayMeta(current_indices=())
        return model.with_value(
            arr_sliced, metadata=meta_sliced, save_behavior_override=NoNeedToSave()
        )

    return run_duplicate_this_slice


@register_function(
    types=StandardType.ARRAY,
    menus=[MenuId.TOOLS_ARRAY],
    command_id="builtins:array:crop",
)
def crop_array(model: WidgetDataModel) -> Parametric:
    """Crop the array."""
    if model.is_subtype_of(StandardType.IMAGE):  # interpret as an image
        from .image import crop_image

        return crop_image(model)

    def _get_selection(*_):
        return _get_current_selection(model)

    @configure_gui(selection={"bind": _get_selection})
    def run_crop_array(
        selection: tuple[tuple[int, int], tuple[int, int]],
    ) -> WidgetDataModel:
        rsl, csl = slice(*selection[0]), slice(*selection[1])
        arr_cropped = wrap_array(model.value)[..., rsl, csl]
        meta_out = _update_meta(model.metadata)
        return model.with_value(arr_cropped, metadata=meta_out).with_title_numbering()

    return run_crop_array


@register_function(
    title="Crop Array (nD)",
    types=StandardType.ARRAY,
    menus=[MenuId.TOOLS_ARRAY],
    command_id="builtins:array:crop-nd",
)
def crop_array_nd(win: SubWindow) -> Parametric:
    """Crop the array in nD."""
    from himena.qt.magicgui import SliderRangeGetter

    model = win.to_model()
    if model.is_subtype_of(StandardType.IMAGE):  # interpret as an image
        from .image import crop_image_nd

        return crop_image_nd(win)

    conf_kwargs = {}
    ndim = wrap_array(model.value).ndim
    for i in range(ndim - 2):
        conf_kwargs[f"axis_{i}"] = {
            "widget_type": SliderRangeGetter,
            "getter": _make_index_getter(win, i),
            "label": f"axis-{i}",
        }

    conf_kwargs[f"axis_{ndim - 2}"] = {
        "bind": lambda: slice(*_get_current_selection(model)[0])
    }
    conf_kwargs[f"axis_{ndim - 1}"] = {
        "bind": lambda: slice(*_get_current_selection(model)[1])
    }

    @configure_gui(gui_options=conf_kwargs)
    def run_crop_array(**kwargs: tuple[int | None, int | None]):
        model = win.to_model()  # NOTE: need to re-fetch the model
        arr = wrap_array(model.value)
        sl_nd = tuple(slice(x0, x1) for x0, x1 in kwargs.values())
        arr_cropped = arr[sl_nd]
        meta_out = _update_meta(model.metadata)
        return model.with_value(arr_cropped, metadata=meta_out).with_title_numbering()

    return run_crop_array


_OPERATOR_CHOICES = [
    ("Add (+)", "add"), ("Subtract (-)", "sub"), ("Multiply (*)", "mul"),
    ("Divide (/)", "truediv"), ("Floor Divide (//)", "floordiv"),
    ("Modulo (%)", "mod"), ("Power (**)", "pow"), ("Bitwise AND (&)", "and_"),
    ("Bitwise OR (|)", "or_"), ("Bitwise XOR (^)", "xor"), ("Equal (==)", "eq"),
    ("Not Equal (!=)", "ne"), ("Greater (>)", "gt"), ("Greater Equal (>=)", "ge"),
    ("Less (<)", "lt"), ("Less Equal (<=)", "le"),
]  # fmt: skip


@register_function(
    title="Binary operation ...",
    menus=[MenuId.TOOLS_ARRAY],
    command_id="builtins:array:binary-operation",
)
def binary_operation() -> Parametric:
    """Calculate +, -, *, /, etc. of two arrays.

    Whether the operation succeeds or not depends on the internal array object. This
    function simply applies the operation to the two arrays and returns the result.
    """

    @configure_gui(
        x={"types": [StandardType.ARRAY]},
        operation={"choices": _OPERATOR_CHOICES},
        y={"types": [StandardType.ARRAY]},
        clip_overflows={
            "tooltip": (
                "If checked, underflow and overflow will be clipped to the minimum \n"
                "maximum value of the data type. Only applicable to the integer data\n"
                "types with +, -, * operations."
            )
        },
    )
    def run_calc(
        x: WidgetDataModel,
        operation: str,
        y: WidgetDataModel,
        clip_overflows: bool = True,
        result_dtype: Literal["as is", "input", "float32", "float64"] = "as is",
    ) -> WidgetDataModel:
        operation_func = getattr(_op, operation)
        if result_dtype == "float32":
            xval = x.value.astype(np.float32, copy=False)
            yval = y.value.astype(np.float32, copy=False)
        elif result_dtype == "float64":
            xval = x.value.astype(np.float64, copy=False)
            yval = y.value.astype(np.float64, copy=False)
        else:
            xval, yval = x.value, y.value
        # get axes from metadata
        if isinstance(meta_x := x.metadata, ImageMeta):
            axes_x = meta_x.axes
        else:
            axes_x = None
        if isinstance(meta_y := y.metadata, ImageMeta):
            axes_y = meta_y.axes
        else:
            axes_y = None
        # broadcast arrays and prepare output axes
        xval, yval, new_axes = _broadcast_arrays(xval, yval, axes_x, axes_y)

        # calculate the operation
        if clip_overflows and operation in ("add", "mul", "sub"):
            arr_out = _safe_op(operation_func, xval, yval, np.dtype(xval.dtype))
        else:
            arr_out = operation_func(xval, yval)
        if result_dtype == "input":
            arr_out = arr_out.astype(xval.dtype, copy=False)
        out = x.with_value(arr_out, title=f"{operation} {x.title} and {y.title}")

        if isinstance(meta := out.metadata, ImageMeta):
            for ch in meta.channels:
                ch.contrast_limits = None  # reset contrast limits
        # inherit axes
        if new_axes is not None and isinstance(meta_out := out.metadata, ArrayMeta):
            meta_out.axes = new_axes
        return out

    return run_calc


@register_function(
    title="Simple calculation ...",
    menus=[MenuId.TOOLS_ARRAY],
    command_id="builtins:array:simple-calculation",
)
def simple_calculation(model: WidgetDataModel) -> Parametric:
    @configure_gui(show_parameter_labels=False)
    def run_calc(expr: str):
        """Python expression to run calculations on the input array.

        Parameters
        ----------
        expr : str
            Python expression to run calculations on the input array. Use symbol `x` for
            the input array.
        """
        from app_model.expressions import safe_eval

        out = safe_eval(expr, {"x": model.value})
        return model.with_value(out).with_title_numbering()

    return run_calc


@register_function(
    title="Convert Data Type (astype) ...",
    menus=[MenuId.TOOLS_ARRAY],
    types=StandardType.ARRAY,
    command_id="builtins:array:astype",
)
def array_astype(model: WidgetDataModel) -> Parametric:
    """Convert the data type of the array using `astype` method."""
    from himena.qt.magicgui import NumericDTypeEdit

    _dtype = str(np.dtype(wrap_array(model.value).dtype))

    @configure_gui(dtype={"widget_type": NumericDTypeEdit, "value": _dtype})
    def run_astype(dtype, inplace: bool = False) -> WidgetDataModel:
        return model.with_value(model.value.astype(dtype), update_inplace=inplace)

    return run_astype


@register_function(
    title="Convert Axis Names ...",
    menus=[MenuId.TOOLS_ARRAY],
    types=StandardType.ARRAY,
    command_id="builtins:array:with-axes",
)
def array_with_axes(model: WidgetDataModel) -> Parametric:
    """Convert the axes of the array."""
    meta = _cast_meta(model, ArrayMeta)
    if (axes := meta.axes) is None:
        raise ValueError("The axes attribute must be set to use this function.")
    gui_options = {}
    for i, axis in enumerate(axes):
        gui_options[f"axis_{i}"] = {
            "widget_type": "LineEdit",
            "value": axis.name,
            "tooltip": "Enter the name of the axis.",
            "label": f"{axis.name} ->",
        }

    @configure_gui(gui_options=gui_options)
    def run_with_axes(**kwargs: str) -> WidgetDataModel:
        meta = _cast_meta(model, ArrayMeta)
        name_old: list[str] = []
        name_new: list[str] = []
        for k, v in kwargs.items():
            axis = axes[int(k[5:])]
            name_old.append(axis.name)
            axis.name = v.strip()
            name_new.append(axis.name)
        set_status_tip(f"Axis names updated: {name_old} -> {name_new}")
        return model.with_metadata(meta, update_inplace=True)

    return run_with_axes


@register_function(
    title="Set scale ...",
    types=StandardType.ARRAY,
    menus=[MenuId.TOOLS_ARRAY],
    command_id="builtins:array:set-scale",
)
def set_scale(model: WidgetDataModel) -> Parametric:
    """Set the axis scales of the array."""
    meta = _cast_meta(model, ArrayMeta)
    if (axes := meta.axes) is None:
        raise ValueError("The axes attribute must be set to use this function.")
    gui_options = {}
    for i, axis in enumerate(axes):
        if axis.unit:
            value = f"{axis.scale:.3f} {axis.unit}"
        else:
            value = f"{axis.scale:.3f}"
        gui_options[f"axis_{i}"] = {
            "widget_type": "LineEdit",
            "value": value,
            "tooltip": "e.g. '0.1', '0.3 um', '500msec'",
            "label": axis.name,
        }

    @configure_gui(gui_options=gui_options)
    def run_set_scale(**kwargs: str):
        meta = _cast_meta(model, ArrayMeta)
        updated_info = []
        for k, v in kwargs.items():
            if v.strip() == "":  # empty string
                scale, unit = None, None
            else:
                scale, unit = _parse_float_and_unit(v)
            axis = axes[int(k[5:])]
            axis.scale = scale
            axis.unit = unit
            if scale is not None:
                if unit:
                    updated_info.append(f"{k}: {scale:.3g} [{unit}]")
                else:
                    updated_info.append(f"{k}: {scale:.3g}")
        updated_info_str = ", ".join(updated_info)
        set_status_tip(f"Scale updated ... {updated_info_str}")
        return model.with_metadata(meta, update_inplace=True)

    return run_set_scale


_C = TypeVar("_C")


def _cast_meta(model: WidgetDataModel, cls: type[_C]) -> _C:
    if not isinstance(meta := model.metadata, cls):
        raise ValueError(
            f"This function is only applicable to models with {cls.__name__}, but got "
            f"metadata of type {type(meta).__name__}."
        )
    return meta


def _get_current_selection_and_meta(
    model: WidgetDataModel,
) -> tuple[tuple[tuple[int, int], tuple[int, int]], ArrayMeta]:
    meta = _cast_meta(model, ArrayMeta)
    if len(sels := meta.selections) != 1:
        raise ValueError(
            f"Single selection is required for this operation (got {len(sels)} "
            "selections)."
        )
    sel = sels[0]
    return sel, meta


def _get_current_selection(
    model: WidgetDataModel,
) -> tuple[tuple[int, int], tuple[int, int]]:
    return _get_current_selection_and_meta(model)[0]


def _make_index_getter(win: SubWindow, ith: int):
    def _getter():
        model = win.to_model()
        meta = _cast_meta(model, ArrayMeta)
        return meta.current_indices[ith]

    return _getter


def _update_meta(metadata: Any) -> ArrayMeta:
    if isinstance(meta := metadata, ArrayMeta):
        meta_out = meta.without_selections()
        meta_out.current_indices = None  # shape changed, need to reset
    else:
        meta_out = ArrayMeta()
    return meta_out


def _parse_float_and_unit(s: str) -> tuple[float, str | None]:
    if " " in s:
        scale, unit = s.split(" ", 1)
        return float(scale), unit
    unit_start = -1
    for i, char in enumerate(s):
        if i == 0:
            continue
        if char == " ":
            unit_start = i + 1
            break
        try:
            float(s[:i])
        except ValueError:
            unit_start = i
            break
    if unit_start == -1:
        return float(s), None
    return float(s[: unit_start - 1]), s[unit_start - 1 :]


_UPCAST_MAP = {
    np.dtype(np.uint8): np.uint16,
    np.dtype(np.uint16): np.int32,
    np.dtype(np.uint32): np.int64,
    np.dtype(np.int8): np.int16,
    np.dtype(np.int16): np.int32,
    np.dtype(np.int32): np.int64,
}


def _upcast(a, dtype):
    try:
        out_dtype = _UPCAST_MAP[dtype]
    except KeyError:
        raise ValueError(f"Cannot upcast {dtype} to a larger type.")
    return a.astype(out_dtype)


def _safe_op(op, a, b, dtype):
    """Add two arrays with overflow/underflow check."""
    if dtype.kind in "iu":
        result_up = op(_upcast(a, dtype), _upcast(b, dtype))
        # NOTE: cannot use the `dtype` argument of `np.clip`.
        return np.clip(
            result_up,
            np.iinfo(dtype).min,
            np.iinfo(dtype).max,
        ).astype(dtype)
    else:
        return a + b


def _broadcast_arrays(
    a: Any,
    b: Any,
    a_axes: list[DimAxis] | None = None,
    b_axes: list[DimAxis] | None = None,
) -> tuple[Any, Any, list[DimAxis] | None]:
    """Broadcast input arrays to the same shape and axes"""
    if a_axes is None or b_axes is None:
        return np.broadcast_arrays(a, b) + (None,)

    # first, make a consensus axes
    arg_idx: list[int] = []
    for ax in b_axes:
        idx_for_ax = _find_axis(a_axes, ax)
        arg_idx.append(idx_for_ax)

    stack: list[int] = []
    n_insert = 0
    axes_consensus = list(a_axes)
    iter = enumerate(arg_idx.copy())
    for i, idx in iter:
        if idx < 0:
            stack.append(i)
        else:
            # flush the stack
            for j in stack:
                axes_consensus.insert(idx + n_insert, b_axes[j])
                n_insert += 1
            stack.clear()
    # flush the stack
    for j in stack:
        axes_consensus.append(b_axes[j])

    # now, broadcast the arrays
    a_slice = []
    b_slice = []
    for ax in axes_consensus:
        if _find_axis(a_axes, ax) < 0:
            a_slice.append(np.newaxis)
        else:
            a_slice.append(slice(None))
        if _find_axis(b_axes, ax) < 0:
            b_slice.append(np.newaxis)
        else:
            b_slice.append(slice(None))
    a_broadcasted = a[tuple(a_slice)]
    b_broadcasted = b[tuple(b_slice)]
    return a_broadcasted, b_broadcasted, axes_consensus


def _find_axis(axes: list[DimAxis], axis: DimAxis) -> int:
    """Find an axis by its name."""
    name = axis.name
    for idx, ax in enumerate(axes):
        if ax.name == name:
            return idx
    return -1
