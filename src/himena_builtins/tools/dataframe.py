from himena.data_wrappers._dataframe import wrap_dataframe
from himena.standards.model_meta import TableMeta
from himena.plugins import register_function, configure_gui
from himena.types import WidgetDataModel, Parametric
from himena.consts import StandardType


@register_function(
    types=StandardType.DATAFRAME,
    menus=["tools/dataframe"],
    command_id="builtins:dataframe:header-to-row",
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
    command_id="builtins:dataframe:series-as-array",
)
def series_as_array(model: WidgetDataModel) -> Parametric:
    """Convert a single column to an array."""

    def _get_column_index(*_):
        c0 = _get_column_selection_name(model)
        if c0 is None:
            raise ValueError("Please select a single column.")
        return c0

    @configure_gui(column={"bind": _get_column_index})
    def run_series_as_array(column: str):
        df = wrap_dataframe(model.value)
        series = df.column_to_array(column)

        return WidgetDataModel(
            value=series,
            title=f"{model.title} ({column})",
            type=StandardType.ARRAY,
            extension_default=".npy",
        )

    return run_series_as_array


@register_function(
    title="Select columns by name ...",
    types=StandardType.DATAFRAME,
    menus=["tools/dataframe"],
    command_id="builtins:dataframe:select-columns-by-name",
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
    command_id="builtins:dataframe:filter",
)
def filter_dataframe(model: WidgetDataModel) -> Parametric:
    import operator as _op

    choices = [
        ("Equal (==)", "eq"), ("Not Equal (!=)", "ne"), ("Greater (>)", "gt"),
        ("Greater Equal (>=)", "ge"), ("Less (<)", "lt"), ("Less Equal (<=)", "le"),
    ]  # fmt: skip
    df = wrap_dataframe(model.value)
    column_names = df.column_names()
    selected_column_name = _get_column_selection_name(model)

    column_name_option = {"choices": column_names}
    if selected_column_name is not None:
        column_name_option["value"] = selected_column_name

    @configure_gui(
        column=column_name_option,
        operator={"choices": choices},
    )
    def run(column: str, operator: str, value: str):
        op_func = getattr(_op, operator)
        series = df[column]
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
    command_id="builtins:dataframe:sort",
)
def sort_dataframe(model: WidgetDataModel) -> Parametric:
    """Sort the DataFrame by a column."""
    df = wrap_dataframe(model.value)
    column_names = df.column_names()

    @configure_gui(
        column={"choices": column_names},
    )
    def run(column: str, descending: bool = False):
        df_new = df.sort(column, descending=descending).unwrap()
        return model.with_value(df_new).with_title_numbering()

    return run


@register_function(
    title="New column using function ...",
    types=StandardType.DATAFRAME,
    menus=["tools/dataframe"],
    command_id="builtins:dataframe:new-column-using-function",
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


def _get_column_selection_name(model: WidgetDataModel) -> str | None:
    if isinstance(meta := model.metadata, TableMeta):
        if len(meta.selections) == 1:
            df = wrap_dataframe(model.value)
            (r0, r1), (c0, c1) = meta.selections[0]
            if r0 == 0 and r1 == df.num_rows() and c1 - c0 == 1:
                return df.column_names()[c0]
    return None
