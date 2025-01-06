from himena._data_wrappers._dataframe import wrap_dataframe
from himena.standards.model_meta import TableMeta
from himena.plugins import register_function, configure_gui
from himena.types import WidgetDataModel, Parametric
from himena.consts import StandardType


@register_function(
    types=StandardType.DATAFRAME,
    menus=["tools/dataframe"],
    command_id="builtins:header-to-row",
)
def header_to_row(model: WidgetDataModel) -> WidgetDataModel:
    """Convert the header as the first row."""
    df = wrap_dataframe(model.value)
    if isinstance(meta := model.metadata, TableMeta):
        sep = meta.separator or ","
    else:
        sep = ","
    csv_string = df.to_csv_string(sep)
    new_columns = [f"column_{i}" for i in range(df.num_columns())]
    input_string = f"{sep.join(new_columns)}\n{csv_string}"
    new_value = df.from_csv_string(input_string, sep)
    return model.with_value(new_value)


@register_function(
    title="Series as array",
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
        type=StandardType.ARRAY,
        extension_default=".npy",
    )


@register_function(
    title="Select columns by name ...",
    types=StandardType.DATAFRAME,
    menus=["tools/dataframe"],
    command_id="builtins:select-columns-by-name",
)
def select_columns_by_name(model: WidgetDataModel):
    df = wrap_dataframe(model.value)

    @configure_gui(
        columns={"choices": df.column_names(), "widget_type": "Select"},
    )
    def run(columns: list[str]):
        df = wrap_dataframe(model.value)
        dict_new = {k: v for k, v in df.to_dict().items() if k in columns}
        df_new = df.from_dict(dict_new)
        return model.with_value(df_new).with_title_numbering()

    return run


@register_function(
    title="New column using function ...",
    types=StandardType.DATAFRAME,
    menus=["tools/dataframe"],
    command_id="builtins:new-column-using-function",
)
def new_column_using_function(model: WidgetDataModel) -> Parametric:
    df = wrap_dataframe(model.value)

    @configure_gui(
        input_column_name={"choices": df.column_names()},
        function={"types": [StandardType.FUNCTION]},
    )
    def run(input_column_name: str, function: WidgetDataModel, output_column_name: str):
        df = wrap_dataframe(model.value)
        col = df[input_column_name]
        out = function.value(col)
        dict_ = df.to_dict()
        dict_[output_column_name] = out
        df_new = df.from_dict(dict_)
        return model.with_value(df_new).with_title_numbering()

    return run
