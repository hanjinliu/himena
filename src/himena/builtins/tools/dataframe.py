from himena.plugins import register_function
from himena.types import WidgetDataModel
from himena.consts import StandardType


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
