from typing import TYPE_CHECKING
from himena.plugins import register_function
from himena.types import WidgetDataModel
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
