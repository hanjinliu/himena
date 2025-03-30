"""Type conversion rules."""

from typing import Literal
from io import StringIO
import re
import csv
import html
import numpy as np
from himena.plugins import configure_gui, register_conversion_rule
from himena.types import Parametric, WidgetDataModel
from himena.consts import StandardType
from himena.core import create_model
from himena.standards.model_meta import TextMeta, TableMeta, DataFrameMeta
from himena.standards.roi import (
    Roi2D,
    RectangleRoi,
    PointRoi2D,
    RoiListModel,
    default_roi_label,
)
from himena.data_wrappers import wrap_dataframe, read_csv, wrap_array
from himena.utils.misc import table_to_text as _table_to_text


@register_conversion_rule(
    type_from=StandardType.TEXT,
    type_to=StandardType.TABLE,
    command_id="builtins:text-to-table",
)
def text_to_table(model: WidgetDataModel[str]) -> WidgetDataModel:
    """Convert text to a table-type widget."""
    buf = StringIO(model.value)
    dialect = csv.Sniffer().sniff(buf.read(1024))
    sep = dialect.delimiter
    buf.seek(0)
    table = np.array(list(csv.reader(buf, delimiter=sep)))
    return create_model(
        table,
        type=StandardType.TABLE,
        title=model.title,
        extension_default=".csv",
    )


@register_conversion_rule(
    type_from=StandardType.TEXT,
    type_to=StandardType.ARRAY,
    command_id="builtins:text-to-array",
)
def text_to_array(model: WidgetDataModel[str]) -> WidgetDataModel:
    """Convert text to an array-type widget using numpy."""
    text = model.value
    arr = np.loadtxt(StringIO(text), delimiter=",")
    return create_model(
        arr,
        type=StandardType.ARRAY,
        title=model.title,
        extension_default=".npy",
    )


@register_conversion_rule(
    type_from=StandardType.TEXT,
    type_to=StandardType.DATAFRAME,
    command_id="builtins:text-to-dataframe",
)
def text_to_dataframe(model: WidgetDataModel[str]) -> WidgetDataModel:
    """Convert text to an dataframe-type widget."""
    from io import StringIO

    buf = StringIO(model.value)
    df = read_csv("dict", buf)
    return create_model(
        df,
        title=model.title,
        type=StandardType.DATAFRAME,
        extension_default=".csv",
    )


@register_conversion_rule(
    type_from=StandardType.HTML,
    type_to=StandardType.TEXT,
    command_id="builtins:to-plain-text",
)
def to_plain_text(model: WidgetDataModel[str]) -> WidgetDataModel:
    """Convert HTML to plain text."""
    html_block_pattern = re.compile(r"<html>.*?</html>", re.DOTALL)
    html_text = model.value
    if html_block_match := html_block_pattern.search(model.value):
        html_text = html_block_match.group(0)
    html_pattern = re.compile(r"<.*?>")
    header_pattern = re.compile(r"<head>.*?</head>", re.DOTALL)
    newline_pattern = re.compile(r"<br\s*/?>", re.IGNORECASE)
    html_text = newline_pattern.sub("\n", html_text)
    value = html.unescape(html_pattern.sub("", header_pattern.sub("", html_text)))
    return model.with_value(value, type=StandardType.TEXT)


@register_conversion_rule(
    type_from=StandardType.DATAFRAME,
    type_to=StandardType.TABLE,
    command_id="builtins:dataframe-to-table",
)
def dataframe_to_table(model: WidgetDataModel) -> WidgetDataModel["np.ndarray"]:
    """Convert a table data into a DataFrame."""
    df = wrap_dataframe(model.value)
    if isinstance(meta := model.metadata, TableMeta):
        # TODO: do we need to inherit current_position and selections?
        separator = meta.separator
    return create_model(
        [df.column_names()] + df.to_list(),
        title=model.title,
        extension_default=".csv",
        metadata=TableMeta(separator=separator),
    )


@register_conversion_rule(
    type_from=StandardType.DATAFRAME,
    type_to=StandardType.TEXT,
    command_id="builtins:dataframe-to-text",
)
def dataframe_to_text(model: WidgetDataModel) -> Parametric:
    """Convert a table data into a DataFrame."""

    def convert_dataframe_to_text(
        format: Literal["CSV", "TSV", "Markdown", "Latex", "rST", "HTML"] = "CSV",
        end_of_text: Literal["", "\\n"] = "\\n",
    ) -> WidgetDataModel[str]:
        df = wrap_dataframe(model.value)
        table_input = df.to_list()
        table_input.insert(0, df.column_names())
        end_of_text = "\n" if end_of_text == "\\n" else ""
        value, ext_default, language = _table_to_text(table_input, format, end_of_text)
        return create_model(
            value,
            title=model.title,
            extension_default=ext_default,
            metadata=TextMeta(language=language),
        )

    return convert_dataframe_to_text


@register_conversion_rule(
    type_from=StandardType.TABLE,
    type_to=StandardType.TEXT,
    command_id="builtins:table-to-text",
)
def table_to_text(model: WidgetDataModel) -> Parametric:
    """Convert a table data into a text data."""

    @configure_gui(
        preview=True, end_of_text={"choices": [("none", ""), ("newline", "\n")]}
    )
    def convert_table_to_text(
        format: Literal["CSV", "TSV", "Markdown", "Latex", "rST", "HTML"] = "CSV",
        end_of_text: Literal["", "\n"] = "\n",
    ) -> WidgetDataModel[str]:
        value, ext_default, language = _table_to_text(model.value, format, end_of_text)
        return create_model(
            value,
            title=model.title,
            extension_default=ext_default,
            metadata=TextMeta(language=language),
        )

    return convert_table_to_text


@register_conversion_rule(
    type_from=StandardType.TABLE,
    type_to=StandardType.DATAFRAME,
    command_id="builtins:table-to-dataframe",
)
def table_to_dataframe(model: WidgetDataModel["np.ndarray"]) -> WidgetDataModel:
    """Convert a table data into a DataFrame."""
    # TODO: Choose pandas, dict etc.
    if isinstance(meta := model.metadata, TableMeta):
        separator = meta.separator
    buf = StringIO()
    np.savetxt(buf, model.value, fmt="%s", delimiter=",")
    buf.seek(0)
    df = read_csv("dict", buf)
    return create_model(
        df,
        title=model.title,
        extension_default=".csv",
        metadata=DataFrameMeta(separator=separator),
    )


@register_conversion_rule(
    type_from=StandardType.TABLE,
    type_to=StandardType.ARRAY,
    command_id="builtins:table-to-array",
)
def table_to_array(model: WidgetDataModel["np.ndarray"]) -> WidgetDataModel:
    """Convert a table data into an array."""
    arr_str = model.value

    def _try_astype(arr_str: "np.ndarray", dtype) -> tuple["np.ndarray", bool]:
        try:
            arr = arr_str.astype(dtype)
            ok = True
        except ValueError:
            arr = arr_str
            ok = False
        return arr, ok

    arr, ok = _try_astype(arr_str, int)
    if not ok:
        arr, ok = _try_astype(arr_str, float)
    if not ok:
        arr, ok = _try_astype(arr_str, complex)
    if not ok:
        pass

    return create_model(
        arr,
        type=StandardType.ARRAY,
        title=model.title,
        extension_default=".npy",
    )


@register_conversion_rule(
    type_from=StandardType.DATAFRAME,
    type_to=StandardType.ROIS,
    command_id="builtins:dataframe-to-image-rois",
)
def dataframe_to_image_rois(model: WidgetDataModel) -> Parametric:
    """Convert a data frame data into image ROIs."""

    @configure_gui(roi_type={"choices": ["rectangle", "point"]})
    def convert_dataframe_to_image_rois(
        roi_type: str,
        indices: list[str] = (),
    ) -> WidgetDataModel:
        df = wrap_dataframe(model.value)
        if indices:
            arr_indice = np.stack(
                [df.column_to_array(indice_column) for indice_column in indices],
                axis=1,
                dtype=np.int32,
            )
        else:
            arr_indice = np.empty((len(df), 0), dtype=np.int32)
        rois: list[Roi2D] = []
        if roi_type == "rectangle":
            arr_xywh = np.stack(
                [
                    df.column_to_array("x"),
                    df.column_to_array("y"),
                    df.column_to_array("width"),
                    df.column_to_array("height"),
                ],
                axis=1,
            )
            for idx, xywh in enumerate(arr_xywh):
                x, y, w, h = xywh
                rois.append(
                    RectangleRoi(
                        name=default_roi_label(idx),
                        x=x,
                        y=y,
                        width=w,
                        height=h,
                    )
                )
        elif roi_type == "point":
            arr_xywh = np.stack(
                [
                    df.column_to_array("x"),
                    df.column_to_array("y"),
                ],
                axis=1,
            )
            for idx, xy in enumerate(arr_xywh):
                x, y = xy
                rois.append(PointRoi2D(name=default_roi_label(idx), x=x, y=y))
        else:
            raise ValueError("Only 'rectangle' and 'point' are supported.")
        return create_model(
            RoiListModel(items=rois, indices=arr_indice, axis_names=indices),
            title=model.title,
            type=StandardType.ROIS,
        )

    return convert_dataframe_to_image_rois


@register_conversion_rule(
    type_from=StandardType.DATAFRAME,
    type_to=StandardType.DATAFRAME_PLOT,
    command_id="builtins:dataframe-to-dataframe-plot",
)
def dataframe_to_dataframe_plot(model: WidgetDataModel) -> WidgetDataModel:
    df = wrap_dataframe(model.value)
    col_non_numerical = [
        col
        for col, dtype in zip(df.column_names(), df.dtypes)
        if dtype.kind not in "uifb"
    ]
    if col_non_numerical:
        raise ValueError(
            f"DataFrame contains non-numerical value in columns {col_non_numerical!r}"
        )
    return model.astype(StandardType.DATAFRAME_PLOT)


@register_conversion_rule(
    type_from=StandardType.ARRAY,
    type_to=StandardType.TABLE,
    command_id="builtins:array-to-table",
)
def array_to_table(model: WidgetDataModel) -> WidgetDataModel:
    """Convert an array data into a table."""
    arr = wrap_array(model.value)
    if arr.ndim > 2:
        raise ValueError("Cannot convert >2D array to a table.")
    value = arr.get_slice(()).astype(np.dtypes.StringDType())
    if value.ndim < 2:
        value = np.atleast_2d(value)
    return create_model(
        value,
        title=model.title,
        type=StandardType.TABLE,
        extension_default=".csv",
    )
