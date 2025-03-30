from typing import TYPE_CHECKING
from himena.standards.model_meta import DictMeta
from himena.plugins import register_function
from himena.types import WidgetDataModel
from himena.consts import StandardType, MenuId
from himena.core import create_model

if TYPE_CHECKING:
    import numpy as np


@register_function(
    title="Duplicate this tab",
    types=StandardType.DICT,
    menus=[MenuId.TOOLS_EXCEL],
    command_id="builtins:duplicate-dict-tab",
)
def duplicate_this_tab(
    model: WidgetDataModel[dict[str, "np.ndarray"]],
) -> WidgetDataModel["np.ndarray"]:
    """Convert the current tab into a separate window"""
    meta, tab = _meta_and_sheet(model)
    if model.type.startswith("dict."):
        type_out = model.type[5:]
    else:
        type_out = model.type
    return create_model(
        model.value[tab],
        title=f"{model.title} ({tab})",
        type=type_out,
        extension_default=".csv",
        metadata=meta.child_meta[tab],
    )


def _meta_and_sheet(model: WidgetDataModel) -> tuple[DictMeta, str]:
    if not isinstance(meta := model.metadata, DictMeta):
        raise ValueError("The input model is not a DictMeta.")
    if (tab := meta.current_tab) is None:
        raise ValueError("The current tab is not specified.")
    return meta, tab
