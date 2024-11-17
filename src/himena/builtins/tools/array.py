from himena.plugins import register_function
from himena.types import WidgetDataModel
from himena.consts import StandardType
from himena.model_meta import ArrayMeta


@register_function(
    types=StandardType.ARRAY,
    menus=["tools/array"],
    command_id="builtins:array-duplicate-slice",
)
def duplicate_this_slice(model: WidgetDataModel) -> WidgetDataModel:
    """Duplicate the slice of the array."""
    from himena._data_wrappers import wrap_array

    if not isinstance(meta := model.additional_data, ArrayMeta):
        raise TypeError(
            "Widget does not have ArrayMeta thus cannot determine the slice indices."
        )
    if (indices := meta.current_indices) is None:
        raise ValueError("The `current_indices` attribute is not set.")
    arr = wrap_array(model.value)
    arr_sliced = arr.get_slice(tuple(indices))
    meta_sliced = ArrayMeta(current_indices=[])
    return model.model_copy(
        update={"value": arr_sliced, "additional_data": meta_sliced}
    )
