from typing import TYPE_CHECKING, Any, TypeVar
from himena._data_wrappers._array import wrap_array
from himena._descriptors import NoNeedToSave
from himena.plugins import register_function, configure_gui
from himena.types import Parametric, WidgetDataModel, is_subtype
from himena.consts import StandardType
from himena.standards.model_meta import ArrayMeta, ImageMeta, ImageAxis, roi as _roi
from himena.widgets._wrapper import SubWindow

if TYPE_CHECKING:
    import numpy as np


@register_function(
    types=StandardType.ARRAY,
    menus=["tools/array"],
    command_id="builtins:array-duplicate-slice",
)
def duplicate_this_slice(model: WidgetDataModel) -> WidgetDataModel:
    """Duplicate the slice of the array."""
    arr_sliced = _get_current_array_2d(model)
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


@register_function(
    types=StandardType.ARRAY,
    menus=["tools/array"],
    command_id="builtins:crop-array",
)
def crop_array(model: WidgetDataModel) -> WidgetDataModel:
    """Crop the array."""
    if is_subtype(model.type, StandardType.IMAGE):  # interpret as an image
        return crop_image(model)
    sel, meta = _get_current_selection_and_meta(model)
    arr_cropped = wrap_array(model.value)[sel]
    return model.with_value(arr_cropped, metadata=meta.without_selections())


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
        return crop_image_nd(model)

    conf_kwargs = {}
    for i in range(wrap_array(model.value).ndim - 2):
        conf_kwargs[f"axis_{i}"] = {
            "widget_type": SliderRangeGetter,
            "getter": _make_getter(win, i),
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
        return model.with_value(arr_cropped, metadata=meta_out)

    return run_crop_image


@register_function(
    types=StandardType.IMAGE,
    menus=["tools/image"],
    command_id="builtins:crop-image",
    keybindings=["Ctrl+Shift+X"],
)
def crop_image(model: WidgetDataModel) -> WidgetDataModel:
    """Crop the image."""
    roi, meta = _get_current_roi_and_meta(model)
    arr = wrap_array(model.value)
    if isinstance(roi, _roi.ImageRoi2D):
        bbox = roi.bbox().adjust_to_int()
        if meta.is_rgb:
            bbox = bbox.limit_to(arr.shape[-3:-1])
        else:
            bbox = bbox.limit_to(arr.shape[-2:])
        ysl = slice(bbox.top, bbox.top + bbox.height + 1)
        xsl = slice(bbox.left, bbox.left + bbox.width + 1)
        if meta.is_rgb:
            arr_cropped = arr[..., ysl, xsl, :]
        else:
            arr_cropped = arr[..., ysl, xsl]
    else:
        raise NotImplementedError
    meta_out = meta.without_rois()
    meta_out.current_roi = roi.shifted(-bbox.left, -bbox.top)
    return model.with_value(arr_cropped, metadata=meta_out)


@register_function(
    title="Crop Image (nD)",
    types=StandardType.IMAGE,
    menus=["tools/image"],
    command_id="builtins:crop-image-nd",
)
def crop_image_nd(win: SubWindow) -> Parametric:
    """Crop the image in nD."""
    from himena.qt._magicgui import SliderRangeGetter

    model = win.to_model()
    ndim = wrap_array(model.value).ndim
    meta = _cast_meta(model, ImageMeta)
    if (axes := meta.axes) is None:
        axes = [ImageAxis(name=f"axis-{i}") for i in range(ndim)]
    index_yx_rgb = 2 + int(meta.is_rgb)
    if ndim < index_yx_rgb + 1:
        raise ValueError("Image only has 2D data.")

    conf_kwargs = {}
    for i, axis in enumerate(axes[:-index_yx_rgb]):
        conf_kwargs[axis.name] = {
            "widget_type": SliderRangeGetter,
            "getter": _make_getter(win, i),
            "label": axis.name,
        }

    @configure_gui(**conf_kwargs)
    def run_crop_image(**kwargs: tuple[int | None, int | None]):
        model = win.to_model()  # NOTE: need to re-fetch the model
        arr = wrap_array(model.value)
        roi, meta = _get_current_roi_and_meta(model)
        sl_nd = tuple(slice(x0, x1) for x0, x1 in kwargs.values())
        if isinstance(roi, _roi.ImageRoi2D):
            bbox = roi.bbox().adjust_to_int()
            if meta.is_rgb:
                bbox = bbox.limit_to(arr.shape[-3:-1])
            else:
                bbox = bbox.limit_to(arr.shape[-2:])
            ysl = slice(bbox.top, bbox.top + bbox.height + 1)
            xsl = slice(bbox.left, bbox.left + bbox.width + 1)
            sl = sl_nd + (ysl, xsl)
            arr_cropped = arr[sl]
        else:
            raise NotImplementedError
        meta_out = meta.without_rois()
        meta_out.current_indices = None  # shape changed, need to reset
        return model.with_value(arr_cropped, metadata=meta_out)

    return run_crop_image


@register_function(
    title="Duplicate ROIs",
    types=StandardType.IMAGE,
    menus=["tools/image"],
    command_id="builtins:duplicate-rois",
)
def duplicate_rois(model: WidgetDataModel) -> WidgetDataModel:
    """Duplicate the ROIs."""
    meta = _cast_meta(model, ImageMeta)
    rois = meta.rois
    if isinstance(rois, _roi.RoiListModel):
        rois = rois.model_copy()
    elif callable(rois):
        rois = rois()
        if not isinstance(rois, _roi.RoiListModel):
            raise ValueError(f"Expected a RoiListModel, got {type(rois)}")
    else:
        raise ValueError("Expected a RoiListModel or a factory function.")
    return WidgetDataModel(
        value=rois,
        type=StandardType.IMAGE_ROIS,
        title=f"ROIs of {model.title}",
    )


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
    title="Data type ...",
    menus=["tools/array"],
    types=StandardType.ARRAY,
    command_id="builtins:array-astype",
)
def array_astype(model: WidgetDataModel) -> Parametric:
    """Convert the data type of the array using `astype` method."""
    from himena.qt._magicgui import NumericDTypeEdit

    @configure_gui(dtype={"widget_type": NumericDTypeEdit})
    def run_astype(dtype) -> WidgetDataModel:
        return model.with_value(model.value.astype(dtype))

    return run_astype


def _get_current_array_2d(model: WidgetDataModel) -> "np.ndarray":
    from himena._data_wrappers import wrap_array

    if not isinstance(meta := model.metadata, ArrayMeta):
        raise TypeError(
            "Widget does not have ArrayMeta thus cannot determine the slice indices."
        )
    if (indices := meta.current_indices) is None:
        raise ValueError("The `current_indices` attribute is not set.")
    arr = wrap_array(model.value)
    return arr.get_slice(tuple(indices))


_C = TypeVar("_C", bound=type)


def _cast_meta(model: WidgetDataModel, cls: type[_C]) -> _C:
    if not isinstance(meta := model.metadata, cls):
        raise ValueError(
            f"This function is only applicable to models with {cls.__name__}, but got "
            f"metadata of type {type(meta).__name__}."
        )
    return meta


def _get_current_roi_and_meta(
    model: WidgetDataModel,
) -> tuple[_roi.ImageRoi2D, ImageMeta]:
    meta = _cast_meta(model, ImageMeta)
    if not (roi := meta.current_roi):
        raise ValueError("ROI selection is required for this operation.")
    return roi, meta


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


def _make_getter(win: SubWindow, ith: int):
    def _getter():
        model = win.to_model()
        meta = _cast_meta(model, ArrayMeta)
        return meta.current_indices[ith]

    return _getter
