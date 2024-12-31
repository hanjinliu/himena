from typing import TYPE_CHECKING, Any, TypeVar
import numpy as np
from himena._data_wrappers._array import wrap_array
from himena._descriptors import NoNeedToSave
from himena.plugins import register_function, configure_gui, run_immediately
from himena.types import Parametric, WidgetDataModel, is_subtype
from himena.consts import StandardType
from himena.standards.model_meta import (
    ArrayMeta,
    ImageMeta,
)
from himena.widgets import set_status_tip, SubWindow

if TYPE_CHECKING:
    import numpy as np


@register_function(
    types=StandardType.ARRAY,
    menus=["tools/array"],
    command_id="builtins:array-duplicate-slice",
    keybindings=["Ctrl+Shift+D"],
)
def duplicate_this_slice(model: WidgetDataModel) -> Parametric:
    """Duplicate the slice of the array."""
    from himena._data_wrappers import wrap_array

    if not isinstance(meta := model.metadata, ArrayMeta):
        raise TypeError(
            "Widget does not have ArrayMeta thus cannot determine the slice indices."
        )
    if (indices := meta.current_indices) is None:
        raise ValueError("The `current_indices` attribute is not set.")

    @run_immediately(indices=indices)
    def run_duplicate_this_slice(indices) -> WidgetDataModel:
        arr = wrap_array(model.value)
        arr_sliced = arr.get_slice(tuple(indices))
        if isinstance(meta := model.metadata, ArrayMeta):
            update = {"current_indices": ()}
            if isinstance(meta, ImageMeta):
                update["axes"] = meta.axes[-2:] if meta.axes is not None else None
                update["channel_axis"] = None
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
    menus=["tools/array"],
    command_id="builtins:crop-array",
)
def crop_array(model: WidgetDataModel) -> WidgetDataModel:
    """Crop the array."""
    if is_subtype(model.type, StandardType.IMAGE):  # interpret as an image
        from .image import crop_image

        return crop_image(model)
    sel, meta = _get_current_selection_and_meta(model)
    arr_cropped = wrap_array(model.value)[sel]
    return model.with_value(
        arr_cropped, metadata=meta.without_selections()
    ).with_title_numbering()


@register_function(
    title="Crop Array (nD)",
    types=StandardType.ARRAY,
    menus=["tools/array"],
    command_id="builtins:crop-array-nd",
)
def crop_array_nd(win: SubWindow) -> Parametric:
    """Crop the array in nD."""
    from himena.qt._magicgui import SliderRangeGetter

    model = win.to_model()
    if is_subtype(model.type, StandardType.IMAGE):  # interpret as an image
        from .image import crop_image_nd

        return crop_image_nd(win)

    conf_kwargs = {}
    for i in range(wrap_array(model.value).ndim - 2):
        conf_kwargs[f"axis_{i}"] = {
            "widget_type": SliderRangeGetter,
            "getter": _make_index_getter(win, i),
            "label": f"axis-{i}",
        }

    @configure_gui(**conf_kwargs)
    def run_crop_image(**kwargs: tuple[int | None, int | None]):
        model = win.to_model()  # NOTE: need to re-fetch the model
        arr = wrap_array(model.value)
        sel, meta = _get_current_selection_and_meta(model)
        sl_nd = tuple(slice(x0, x1) for x0, x1 in kwargs.values())
        sl = sl_nd + tuple(sel)
        arr_cropped = arr[sl]
        meta_out = meta.without_selections()
        meta_out.current_indices = None  # shape changed, need to reset
        return model.with_value(arr_cropped, metadata=meta_out).with_title_numbering()

    return run_crop_image


@register_function(
    title="Binary operation ...",
    menus=["tools/array"],
    command_id="builtins:binary-operation",
)
def binary_operation() -> Parametric:
    """Calculate +, -, *, /, etc. of two arrays.

    Whether the operation succeeds or not depends on the internal array object. This
    function simply applies the operation to the two arrays and returns the result.
    """
    import operator as _op

    choices = [
        ("Add (+)", _op.add), ("Subtract (-)", _op.sub), ("Multiply (*)", _op.mul),
        ("Divide (/)", _op.truediv), ("Floor Divide (//)", _op.floordiv),
        ("Modulo (%)", _op.mod), ("Power (**)", _op.pow), ("Bitwise AND (&)", _op.and_),
        ("Bitwise OR (|)", _op.or_), ("Bitwise XOR (^)", _op.xor),
    ]  # fmt: skip

    @configure_gui(
        x={"types": [StandardType.ARRAY]},
        operation={"choices": choices},
        y={"types": [StandardType.ARRAY]},
    )
    def run_calc(
        x: WidgetDataModel,
        operation,
        y: WidgetDataModel,
    ) -> WidgetDataModel:
        arr_out = operation(x.value, y.value)
        op_name = operation.__name__.strip("_")
        return x.with_value(arr_out, title=f"{op_name} {x.title} and {y.title}")

    return run_calc


@register_function(
    title="Simple calculation ...",
    menus=["tools/array"],
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
    menus=["tools/array"],
    types=StandardType.ARRAY,
    command_id="builtins:array-astype",
)
def array_astype(model: WidgetDataModel) -> Parametric:
    """Convert the data type of the array using `astype` method."""
    from himena.qt._magicgui import NumericDTypeEdit

    _dtype = np.dtype(wrap_array(model.value).dtype)

    @configure_gui(dtype={"widget_type": NumericDTypeEdit, "value": _dtype})
    def run_astype(dtype) -> WidgetDataModel:
        return model.with_value(model.value.astype(dtype))

    return run_astype


@register_function(
    title="Set scale ...",
    types=StandardType.ARRAY,
    menus=["tools/array"],
    command_id="builtins:set-array-scale",
)
def set_scale(win: SubWindow) -> Parametric:
    model = win.to_model()
    meta = _cast_meta(model, ArrayMeta)
    if (axes := meta.axes) is None:
        raise ValueError("The axes attribute must be set to use this function.")
    gui_options = {}
    for axis in axes:
        if axis.scale is None:
            value = ""
        elif axis.unit is None:
            value = f"{axis.scale:.3f}"
        else:
            value = f"{axis.scale:.3f} {axis.unit}"
        gui_options[axis.name] = {
            "widget_type": "LineEdit",
            "value": value,
            "tooltip": "e.g. '0.1', '0.3 um', '500msec'",
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
            for axis in meta.axes:
                if axis.name == k:
                    axis.scale = scale
                    axis.unit = unit
                    break
            if scale is not None:
                if unit is None:
                    updated_info.append(f"{k}: {scale:.3g}")
                else:
                    updated_info.append(f"{k}: {scale:.3g} [{unit}]")
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
) -> tuple[Any, ArrayMeta]:
    meta = _cast_meta(model, ArrayMeta)
    if len(sels := meta.selections) != 1:
        raise ValueError(
            f"Single selection is required for this operation (got {len(sels)} "
            "selections)."
        )
    sel = sels[0]
    return sel, meta


def _make_index_getter(win: SubWindow, ith: int):
    def _getter():
        model = win.to_model()
        meta = _cast_meta(model, ArrayMeta)
        return meta.current_indices[ith]

    return _getter


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
