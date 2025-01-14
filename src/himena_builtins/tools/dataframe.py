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
def select_columns_by_name(model: WidgetDataModel) -> Parametric:
    df = wrap_dataframe(model.value)

    @configure_gui(
        columns={"choices": df.column_names(), "widget_type": "Select"},
    )
    def run(columns: list[str]):
        df_new = wrap_dataframe(model.value).select(columns).unwrap()
        return model.with_value(df_new).with_title_numbering()

    return run


@register_function(
    title="Filter DataFrame ...",
    types=StandardType.DATAFRAME,
    menus=["tools/dataframe"],
    command_id="builtins:filter-dataframe",
)
def filter_dataframe(model: WidgetDataModel) -> Parametric:
    import operator as _op

    choices = [
        ("Equal (==)", "eq"), ("Not Equal (!=)", "ne"), ("Greater (>)", "gt"),
        ("Greater Equal (>=)", "ge"), ("Less (<)", "lt"), ("Less Equal (<=)", "le"),
    ]  # fmt: skip
    df = wrap_dataframe(model.value)
    column_names = df.column_names()
    selected_column_name = None
    if isinstance(meta := model.metadata, TableMeta):
        if len(meta.selections) == 1:
            (r0, r1), (c0, c1) = meta.selections[0]
            if r0 == 0 and r1 == df.num_rows() and c1 - c0 == 1:
                selected_column_name = column_names[c0]

    column_name_option = {"choices": column_names}
    if selected_column_name is not None:
        column_name_option["value"] = selected_column_name

    @configure_gui(
        column_name=column_name_option,
        operator={"choices": choices},
    )
    def run(column_name: str, operator: str, value: str):
        op_func = getattr(_op, operator)
        series = df[column_name]
        if series.dtype.kind in "iuf":
            value_parsed = float(value)
        elif series.dtype.kind == "b":
            value_parsed = value.lower() in ["true", "1"]
        elif series.dtype.kind == "c":
            value_parsed = complex(value)
        value_parsed = value
        sl = op_func(series, value_parsed)
        df_new = df.filter(sl).unwrap()
        return model.with_value(df_new).with_title_numbering()

    return run


@register_function(
    title="Sort DataFrame ...",
    types=StandardType.DATAFRAME,
    menus=["tools/dataframe"],
    command_id="builtins:sort-dataframe",
)
def sort_dataframe(model: WidgetDataModel) -> Parametric:
    """Sort the DataFrame by a column."""
    df = wrap_dataframe(model.value)
    column_names = df.column_names()

    @configure_gui(
        column_name={"choices": column_names},
    )
    def run(column_name: str, descending: bool = False):
        df_new = df.sort(column_name, descending=descending).unwrap()
        return model.with_value(df_new).with_title_numbering()

    return run


@register_function(
    title="New column using function ...",
    types=StandardType.DATAFRAME,
    menus=["tools/dataframe"],
    command_id="builtins:new-column-using-function",
)
def new_column_using_function(model: WidgetDataModel) -> Parametric:
    """Add a new column using a user-defined function."""
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
