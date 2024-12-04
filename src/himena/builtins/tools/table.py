from io import StringIO
from typing import Literal
import numpy as np

from himena.plugins import register_function, configure_gui
from himena.types import Parametric, WidgetDataModel
from himena.standards.model_meta import TableMeta, TextMeta
from himena.consts import StandardType


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


@register_function(
    title="Convert table to text ...",
    types=StandardType.TABLE,
    menus=["tools/table"],
    command_id="builtins:table-to-text",
)
def table_to_text(model: WidgetDataModel) -> Parametric:
    """Convert a table data into a text data."""

    @configure_gui(preview=True)
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


@register_function(
    title="Convert table to DataFrame ...",
    types=StandardType.TABLE,
    menus=["tools/table"],
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


@register_function(
    title="Convert table to array ...",
    types=StandardType.TABLE,
    menus=["tools/table"],
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
        arr = _try_astype(arr_str, complex)

    return WidgetDataModel(
        value=arr,
        type=StandardType.ARRAY,
        title=model.title,
        extension_default=".npy",
    )


@register_function(
    title="Crop selection",
    types=StandardType.TABLE,
    menus=["tools/table"],
    command_id="builtins:crop-selection",
)
def crop_selection(model: WidgetDataModel["np.ndarray"]) -> WidgetDataModel:
    """Crop the table data at the selection."""
    arr_str = model.value
    if isinstance(meta := model.metadata, TableMeta):
        sels = meta.selections
        if sels is None or len(sels) != 1:
            raise ValueError("Table must contain single selection to crop.")
        (r0, r1), (c0, c1) = sels[0]
        arr_new = arr_str[r0:r1, c0:c1]
        out = model.with_value(arr_new)
        if isinstance(meta := out.metadata, TableMeta):
            meta.selections = []
        return out
    raise ValueError("Table must have a TableMeta as the metadata")


@register_function(
    title="Change separator ...",
    types=StandardType.TABLE,
    menus=["tools/table"],
    command_id="builtins:table-change-separator",
)
def change_separator(model: WidgetDataModel["np.ndarray"]) -> Parametric:
    """Change the separator of the table data."""
    arr_str = model.value
    if not isinstance(meta := model.metadata, TableMeta):
        raise ValueError("Table must have a TableMeta as the metadata")
    sep = meta.separator
    if sep is None:
        raise ValueError("Current separator of the table is unknown.")

    @configure_gui(
        title="Change separator",
        preview=True,
    )
    def change_separator(separator: str = ",") -> WidgetDataModel:
        buf = StringIO()
        np.savetxt(buf, arr_str, fmt="%s", delimiter=sep)
        buf.seek(0)
        arr_new = np.loadtxt(
            buf,
            delimiter=separator.encode().decode("unicode_escape"),
            dtype=np.dtypes.StringDType(),
        )
        return model.with_value(arr_new)

    return change_separator
