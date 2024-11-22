from typing import Literal
from himena._data_wrappers._dataframe import wrap_dataframe
from himena.model_meta import TextMeta
from himena.plugins import register_function
from himena.types import Parametric, WidgetDataModel
from himena.consts import StandardType
from himena.model_meta import DataFrameMeta
from himena.builtins.tools.table import _table_to_text


@register_function(
    title="Convert DataFrame to Table ...",
    types=StandardType.DATAFRAME,
    menus=["tools/dataframe"],
    command_id="builtins:dataframe-to-table",
)
def dataframe_to_table(model: WidgetDataModel) -> WidgetDataModel[list[list[str]]]:
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
            additional_data=TextMeta(language=language),
        )

    return convert_table_to_text


@register_function(
    types=StandardType.DATAFRAME,
    menus=["tools/dataframe"],
    command_id="builtins:dataframe-plot-scatter",
)
def plot_scatter(model: WidgetDataModel) -> WidgetDataModel:
    """Plot the array as a scatter plot."""
    if not isinstance(meta := model.additional_data, DataFrameMeta):
        raise TypeError(
            "Widget does not have DataFrameMeta thus cannot determine the slice indices."
        )
    sels = meta.selections
    if len(sels) == 0:
        raise ValueError("No selections are made.")
    if len(sels) == 1:
        (r0, r1), (c0, c1) = sels[0]
        wrap_dataframe(model.value).get_subset(r0, r1, c0, c1)

        # return WidgetDataModel
