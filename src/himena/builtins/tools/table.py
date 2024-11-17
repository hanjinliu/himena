from typing import Literal
from himena.plugins import register_function, configure_gui
from himena.types import Parametric, WidgetDataModel
from himena.model_meta import TextMeta
from himena.consts import StandardType


def _table_to_latex(table: list[list[str]]) -> str:
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
    data: list[list[str]],
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
    preview=True,
    command_id="builtins:table-to-text",
)
def table_to_text(model: WidgetDataModel) -> Parametric[str]:
    """Convert a table data into a text data."""

    def convert_table_to_text(
        format: Literal["CSV", "TSV", "Markdown", "Latex", "rST", "HTML"] = "CSV",
        end_of_text: Literal["", "\n"] = "\n",
    ) -> WidgetDataModel[str]:
        value, ext_default, language = _table_to_text(model.value, format, end_of_text)
        return WidgetDataModel(
            value=value,
            type=StandardType.TEXT,
            title=f"{model.title} (as text)",
            extension_default=ext_default,
            additional_data=TextMeta(language=language),
        )

    return convert_table_to_text


@register_function(
    title="Convert table to DataFrame ...",
    types=StandardType.TABLE,
    menus=["tools/table"],
    command_id="builtins:table-to-dataframe",
)
def table_to_dataframe(model: WidgetDataModel) -> Parametric[str]:
    """Convert a table data into a DataFrame."""
    from io import StringIO
    from himena._data_wrappers import list_installed_dataframe_packages, read_csv

    pkgs = list_installed_dataframe_packages()
    if len(pkgs) == 0:
        raise ValueError(
            "No DataFrame package is installed. Please install one of the following "
            "packages: `pandas`, `polars`, `pyarrow`."
        )

    @configure_gui(module={"choices": pkgs})
    def convert_table_to_dataframe(module) -> WidgetDataModel[str]:
        csv = "\n".join(",".join(row) for row in model.value)
        buf = StringIO(csv)
        df = read_csv(module, buf)
        return WidgetDataModel(
            value=df,
            title=f"{model.title} (as dataframe)",
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
def table_to_array(model: WidgetDataModel) -> WidgetDataModel:
    """Convert a table data into an array."""
    import numpy as np

    arr_str = np.array(model.value)

    def _try_astype(arr_str: np.ndarray, dtype) -> tuple[np.ndarray, bool]:
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
