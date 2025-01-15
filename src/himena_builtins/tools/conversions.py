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
from himena.standards.model_meta import TextMeta
from himena.standards.roi import (
    Roi2D,
    RectangleRoi,
    PointRoi2D,
    RoiListModel,
    default_roi_label,
)
from himena._data_wrappers import (
    wrap_dataframe,
    read_csv,
)


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
    return WidgetDataModel(
        value=table,
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
    return WidgetDataModel(
        value=arr,
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
    return WidgetDataModel(
        value=df,
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
    return WidgetDataModel(
        value=[df.column_names()] + df.to_list(),
        title=model.title,
        type=StandardType.TABLE,
        extension_default=".csv",
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
        return WidgetDataModel(
            value=value,
            title=model.title,
            type=StandardType.TEXT,
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
        return WidgetDataModel(
            value=value,
            type=StandardType.TEXT,
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

    buf = StringIO()
    np.savetxt(buf, model.value, fmt="%s", delimiter=",")
    buf.seek(0)
    df = read_csv("dict", buf)
    return WidgetDataModel(
        value=df,
        title=model.title,
        type=StandardType.DATAFRAME,
        extension_default=".csv",
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

    return WidgetDataModel(
        value=arr,
        type=StandardType.ARRAY,
        title=model.title,
        extension_default=".npy",
    )


@register_conversion_rule(
    type_from=StandardType.DATAFRAME,
    type_to=StandardType.ROIS,
    command_id="builtins:dataframe-to-image_rois",
)
def dataframe_to_image_rois(model: WidgetDataModel) -> Parametric:
    """Convert a data frame data into image ROIs."""

    @configure_gui(roi_type={"choices": ["rectangle", "point"]})
    def convert_dataframe_to_image_rois(
        roi_type: str, indices: list[str]
    ) -> WidgetDataModel:
        df = wrap_dataframe(model.value)
        if indices:
            arr_indice = np.stack(
                [df.column_to_array(indice_column) for indice_column in indices], axis=1
            )
        else:
            arr_indice = np.empty((len(df), 0), dtype=int)
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
            for idx, (indice, xywh) in enumerate(zip(arr_indice, arr_xywh)):
                x, y, w, h = xywh
                rois.append(
                    RectangleRoi(
                        indices=tuple(indice),
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
            for idx, (indice, xy) in enumerate(zip(arr_indice, arr_xywh)):
                x, y = xy
                rois.append(
                    PointRoi2D(
                        indices=tuple(indice), name=default_roi_label(idx), x=x, y=y
                    )
                )
        else:
            raise ValueError("Only 'rectangle' and 'point' are supported.")
        value = RoiListModel(rois=rois)
        return WidgetDataModel(
            value=value,
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


def _table_to_text(
    data: "np.ndarray",
    format: Literal["CSV", "TSV", "Markdown", "Latex", "rST", "HTML"] = "CSV",
    end_of_text: Literal["", "\n"] = "\n",
) -> tuple[str, str, str]:
    from tabulate import tabulate

    format = format.lower()
    if format == "markdown":
        s = tabulate(data, tablefmt="github")
        ext_default = ".md"
        language = "markdown"
    elif format == "latex":
        s = _table_to_latex(data)
        ext_default = ".tex"
        language = "latex"
    elif format == "html":
        s = tabulate(data, tablefmt="html")
        ext_default = ".html"
        language = "html"
    elif format == "rst":
        s = tabulate(data, tablefmt="rst")
        ext_default = ".rst"
        language = "rst"
    elif format == "csv":
        s = "\n".join(",".join(row) for row in data)
        ext_default = ".csv"
        language = None
    elif format == "tsv":
        s = "\n".join("\t".join(row) for row in data)
        ext_default = ".tsv"
        language = None
    else:
        raise ValueError(f"Unknown format: {format}")
    return s + end_of_text, ext_default, language


def _table_to_latex(table: "np.ndarray") -> str:
    """Convert a table to LaTeX."""
    header = table[0]
    body = table[1:]
    latex = "\\begin{tabular}{" + "c" * len(header) + "}\n"
    latex += " & ".join(header) + " \\\\\n"
    for row in body:
        latex += " & ".join(row) + " \\\\\n"
    latex += "\\hline\n"
    latex += "\\end{tabular}"
    return latex
