from typing import Literal
from himena.model_meta import TextMeta
from himena.plugins import register_function
from himena.types import WidgetDataModel
from himena.consts import StandardType
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

    return WidgetDataModel(
        value=wrap_dataframe(model.value).to_list(),
        title=f"{model.title} (as dataframe)",
        type=StandardType.TABLE,
        extension_default=".csv",
    )


@register_function(
    title="Convert DataFrame to Text ...",
    types=StandardType.DATAFRAME,
    menus=["tools/dataframe"],
    command_id="builtins:dataframe-to-text",
)
def dataframe_to_text(model: WidgetDataModel) -> WidgetDataModel[str]:
    """Convert a table data into a DataFrame."""
    from himena._data_wrappers import wrap_dataframe

    table_input = wrap_dataframe(model.value).to_list()

    def convert_table_to_text(
        format: Literal["CSV", "TSV", "Markdown", "Latex", "rST", "HTML"] = "CSV",
        end_of_text: Literal["", "\n"] = "\n",
    ) -> WidgetDataModel[str]:
        value, ext_default, language = _table_to_text(table_input, format, end_of_text)
        return WidgetDataModel(
            value=value,
            title=f"{model.title} (as dataframe)",
            type=StandardType.TEXT,
            extension_default=ext_default,
            additional_data=TextMeta(language=language),
        )
