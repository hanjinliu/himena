from typing import Any, Literal, TypeVar
import operator as _op
import numpy as np
from himena.data_wrappers._array import wrap_array
from himena._descriptors import NoNeedToSave
from himena.plugins import register_function, configure_gui
from himena.types import Parametric, WidgetDataModel
from himena.utils.misc import is_subtype
from himena.consts import StandardType, MenuId
from himena.standards.model_meta import ArrayMeta, ImageMeta
from himena.widgets import set_status_tip, SubWindow


@register_function(
    types=StandardType.ARRAY,
    menus=[MenuId.TOOLS_ARRAY],
    command_id="builtins:array-duplicate-slice",
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
            update = {"current_indices": ()}
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
    command_id="builtins:crop-array",
)
def crop_array(model: WidgetDataModel) -> Parametric:
    """Crop the array."""
    if is_subtype(model.type, StandardType.IMAGE):  # interpret as an image
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
    command_id="builtins:crop-array-nd",
)
def crop_array_nd(win: SubWindow) -> Parametric:
    """Crop the array in nD."""
    from himena.qt.magicgui import SliderRangeGetter

    model = win.to_model()
    if is_subtype(model.type, StandardType.IMAGE):  # interpret as an image
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
    def run_crop_image(**kwargs: tuple[int | None, int | None]):
        model = win.to_model()  # NOTE: need to re-fetch the model
        arr = wrap_array(model.value)
        sl_nd = tuple(slice(*_x) for _x in kwargs.values())
        arr_cropped = arr[sl_nd]
        meta_out = _update_meta(model.metadata)
        return model.with_value(arr_cropped, metadata=meta_out).with_title_numbering()

    return run_crop_image


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
    command_id="builtins:binary-operation",
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
                "If checked, underflow will be clipped to 0, and "
                "overflow will be \n"
                "clipped to the maximum value of the data type. Only applicable to \n"
                "integer data types with +, -, *, ** operations."
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
        arr_out = operation_func(xval, yval)
        if clip_overflows:
            if operation in ("add", "mul", "pow"):
                _replace_overflows(xval, yval, arr_out)
            elif operation == "sub":
                _replace_underflows(xval, yval, arr_out)
        if result_dtype == "input":
            arr_out = arr_out.astype(xval.dtype, copy=False)
        return x.with_value(arr_out, title=f"{operation} {x.title} and {y.title}")

    return run_calc


@register_function(
    title="Simple calculation ...",
    menus=[MenuId.TOOLS_ARRAY],
    command_id="builtins:simple-calculation",
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
    title="Convert data type (astype) ...",
    menus=[MenuId.TOOLS_ARRAY],
    types=StandardType.ARRAY,
    command_id="builtins:array-astype",
)
def array_astype(model: WidgetDataModel) -> Parametric:
    """Convert the data type of the array using `astype` method."""
    from himena.qt.magicgui import NumericDTypeEdit

    _dtype = str(np.dtype(wrap_array(model.value).dtype))

    @configure_gui(dtype={"widget_type": NumericDTypeEdit, "value": _dtype})
    def run_astype(dtype) -> WidgetDataModel:
        return model.with_value(model.value.astype(dtype))

    return run_astype


@register_function(
    title="Set scale ...",
    types=StandardType.ARRAY,
    menus=[MenuId.TOOLS_ARRAY],
    command_id="builtins:set-array-scale",
)
def set_scale(win: SubWindow) -> Parametric:
    model = win.to_model()
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
        model = win.to_model()
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
        win.update_model(model.model_copy(update={"metadata": meta}))
        updated_info_str = ", ".join(updated_info)
        set_status_tip(f"Scale updated ... {updated_info_str}")
        return

    return run_set_scale


_C = TypeVar("_C", bound=type)


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


def _replace_overflows(a, b, result):
    if result.dtype.kind not in "iu":
        return
    overflow_region = (result < a) | (result < b)
    result[overflow_region] = np.iinfo(result.dtype).max


def _replace_underflows(a, b, result):
    if result.dtype.kind not in "iu":
        return
    underflow_region = (result > a) | (result > b)
    result[underflow_region] = np.iinfo(result.dtype).min
