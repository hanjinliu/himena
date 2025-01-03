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
def text_to_dataframe(model: WidgetDataModel[str]) -> Parametric:
    """Convert text to an dataframe-type widget."""
    from io import StringIO
    from himena._data_wrappers import list_installed_dataframe_packages, read_csv

    @configure_gui(module={"choices": list_installed_dataframe_packages()})
    def convert_text_to_dataframe(module) -> WidgetDataModel[str]:
        buf = StringIO(model.value)
        df = read_csv(module, buf)
        return WidgetDataModel(
            value=df,
            title=model.title,
            type=StandardType.DATAFRAME,
            extension_default=".csv",
        )

    return convert_text_to_dataframe


@register_conversion_rule(
    type_from=StandardType.HTML,
    type_to=StandardType.TEXT,
    command_id="builtins:to-plain-text",
)
def to_plain_text(model: WidgetDataModel[str]) -> WidgetDataModel:
    """Convert HTML to plain text."""
    html_pattern = re.compile(r"<.*?>")
    header_pattern = re.compile(r"<head>.*?</head>", re.DOTALL)
    value = html.unescape(
        html_pattern.sub("", header_pattern.sub("", model.value).replace("<br>", "\n"))
    )
    return model.with_value(value)


@register_conversion_rule(
    type_from=StandardType.DATAFRAME,
    type_to=StandardType.TABLE,
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


@register_conversion_rule(
    type_from=StandardType.DATAFRAME,
    type_to=StandardType.TEXT,
    command_id="builtins:dataframe-to-text",
)
def dataframe_to_text(model: WidgetDataModel) -> Parametric:
    """Convert a table data into a DataFrame."""
    from himena._data_wrappers import wrap_dataframe

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
def table_to_dataframe(model: WidgetDataModel["np.ndarray"]) -> Parametric:
    """Convert a table data into a DataFrame."""
    from himena._data_wrappers import list_installed_dataframe_packages, read_csv

    @configure_gui(module={"choices": list_installed_dataframe_packages()})
    def convert_table_to_dataframe(module) -> WidgetDataModel[str]:
        buf = StringIO()
        np.savetxt(buf, model.value, fmt="%s", delimiter=",")
        buf.seek(0)
        df = read_csv(module, buf)
        return WidgetDataModel(
            value=df,
            title=model.title,
            type=StandardType.DATAFRAME,
            extension_default=".csv",
        )

    return convert_table_to_dataframe


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
