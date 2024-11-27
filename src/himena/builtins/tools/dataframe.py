from typing import Literal, TYPE_CHECKING
from himena._data_wrappers._dataframe import wrap_dataframe
from himena.model_meta import TableMeta, TextMeta
from himena.plugins import register_function
from himena.types import Parametric, WidgetDataModel
from himena.consts import StandardType
from himena.builtins.tools.table import _table_to_text

if TYPE_CHECKING:
    import numpy as np


@register_function(
    title="Convert DataFrame to Table ...",
    types=StandardType.DATAFRAME,
    menus=["tools/dataframe"],
    command_id="builtins:dataframe-to-table",
)
def dataframe_to_table(model: WidgetDataModel) -> WidgetDataModel["np.ndarray"]:
    """Convert a table data into a DataFrame."""
    from himena._data_wrappers import wrap_dataframe

    df = wrap_dataframe(model.value)
    return WidgetDataModel(
        value=[df.column_names()] + df.to_list(),
        title=model.title,
        type=StandardType.TABLE,
        extension_default=".csv",
    )


@register_function(
    title="Convert DataFrame to Text ...",
    types=StandardType.DATAFRAME,
    menus=["tools/dataframe"],
    command_id="builtins:dataframe-to-text",
)
def dataframe_to_text(model: WidgetDataModel) -> Parametric:
    """Convert a table data into a DataFrame."""
    from himena._data_wrappers import wrap_dataframe

    table_input = wrap_dataframe(model.value).to_list()

    def convert_table_to_text(
        format: Literal["CSV", "TSV", "Markdown", "Latex", "rST", "HTML"] = "CSV",
        end_of_text: Literal["", "\\n"] = "\\n",
    ) -> WidgetDataModel[str]:
        end_of_text = "\n" if end_of_text == "\\n" else ""
        value, ext_default, language = _table_to_text(table_input, format, end_of_text)
        return WidgetDataModel(
            value=value,
            title=model.title,
            type=StandardType.TEXT,
            extension_default=ext_default,
            metadata=TextMeta(language=language),
        )

    return convert_table_to_text


# @register_function(
#     types=StandardType.DATAFRAME,
#     menus=["tools/dataframe"],
#     command_id="builtins:series-as-array",
# )
# def header_to_row(model: WidgetDataModel) -> WidgetDataModel:
#     df = wrap_dataframe(model.value)
#     df.column_names()

#     return WidgetDataModel(
#         value=row,
#         title=f"{model.title} (Row {r0})",
#         type=StandardType.ARRAY_1D,
#         extension_default=".npy",
#     )


@register_function(
    types=StandardType.DATAFRAME,
    menus=["tools/dataframe"],
    command_id="builtins:series-as-array",
)
def series_as_array(model: WidgetDataModel) -> WidgetDataModel:
    if not isinstance(meta := model.metadata, TableMeta):
        raise TypeError(
            "Widget does not have DataFrameMeta thus cannot determine the slice indices."
        )
    sels = meta.selections
    if len(sels) != 1:
        raise ValueError("Only one selection is allowed for this operation.")

    (r0, r1), (c0, c1) = sels[0]
    if c0 + 1 != c1:
        raise ValueError("Only one column can be selected.")
    df = wrap_dataframe(model.value)
    if r0 != 0 or r1 != df.num_rows():
        raise ValueError("Current selection is not a column.")
    column_name = df.column_names()[c0]
    series = df.column_to_array(column_name)

    return WidgetDataModel(
        value=series,
        title=f"{model.title} ({column_name})",
        type=StandardType.ARRAY_1D,
        extension_default=".npy",
    )
