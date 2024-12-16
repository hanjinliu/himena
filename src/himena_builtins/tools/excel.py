from typing import TYPE_CHECKING
from himena.standards.model_meta import ExcelMeta, TableMeta
from himena.plugins import register_function
from himena.types import WidgetDataModel
from himena.consts import StandardType

if TYPE_CHECKING:
    import numpy as np


@register_function(
    title="Duplicate Sheet as Table",
    types=StandardType.EXCEL,
    menus=["tools/excel"],
    command_id="builtins:duplicate-sheet-as-table",
)
def duplicate_sheet_as_table(
    model: WidgetDataModel[dict[str, "np.ndarray"]],
) -> WidgetDataModel["np.ndarray"]:
    """Convert the current sheet into a table."""
    meta, sheet = _meta_and_sheet(model)

    return WidgetDataModel(
        value=model.value[sheet],
        title=f"{model.title} ({sheet})",
        type=StandardType.TABLE,
        extension_default=".csv",
        metadata=TableMeta(
            current_position=meta.current_position,
            selections=meta.selections,
        ),
    )


def _meta_and_sheet(model: WidgetDataModel) -> tuple[ExcelMeta, str]:
    if not isinstance(meta := model.metadata, ExcelMeta):
        raise ValueError("The input model is not an Excel model.")
    if (sheet := meta.current_sheet) is None:
        raise ValueError("The current sheet is not specified.")
    return meta, sheet
