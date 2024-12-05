from typing import TYPE_CHECKING
from himena._data_wrappers._array import wrap_array
from himena.plugins import register_function
from himena.standards.roi.core import ImageRoi2D
from himena.types import WidgetDataModel, is_subtype
from himena.consts import StandardType
from himena.standards.model_meta import ArrayMeta, ImageMeta

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
            update["scale"] = meta.scale[-2:] if meta.scale is not None else None
            update["origin"] = meta.origin[-2:] if meta.origin is not None else None
            update["channel_axis"] = None
        meta_sliced = meta.model_copy(update=update)
    else:
        meta_sliced = ArrayMeta(current_indices=())
    return model.with_value(arr_sliced, metadata=meta_sliced)


@register_function(
    types=StandardType.ARRAY,
    menus=["tools/array"],
    command_id="builtins:crop-array",
)
def crop_array(model: WidgetDataModel) -> WidgetDataModel:
    """Crop the array."""
    if is_subtype(model.type, StandardType.IMAGE):
        return crop_image(model)

    if not isinstance(meta := model.metadata, ArrayMeta):
        raise ValueError("This function is only applicable to models with ArrayMeta.")
    if len(sels := meta.selections) != 1:
        raise ValueError("Single selection is required for this operation.")
    sel = sels[0]
    arr_cropped = wrap_array(model.value)[sel]
    return model.with_value(arr_cropped, metadata=meta.without_selections())


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
    if isinstance(roi, ImageRoi2D):
        bbox = roi.bbox().adjust_to_int()
        ysl = slice(bbox.top, bbox.top + bbox.height + 1)
        xsl = slice(bbox.left, bbox.left + bbox.width + 1)
        if meta.is_rgb:
            arr_cropped = arr[..., ysl, xsl, :]
        else:
            arr_cropped = arr[..., ysl, xsl]
    else:
        raise NotImplementedError
    return model.with_value(arr_cropped, metadata=meta.without_rois())


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


def _get_current_roi_and_meta(model: WidgetDataModel) -> tuple[ImageRoi2D, ImageMeta]:
    if not isinstance(meta := model.metadata, ImageMeta):
        raise ValueError(
            "This function is only applicable to models with ImageMeta, but got "
            f"metadata of type {type(meta).__name__}."
        )
    if not (roi := meta.current_roi):
        raise ValueError("ROI selection is required for this operation.")
    return roi, meta
