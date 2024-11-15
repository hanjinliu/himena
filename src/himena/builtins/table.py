from typing import Literal
import importlib
from himena.plugins import register_function
from himena.types import Parametric, WidgetDataModel
from himena.model_meta import TextMeta
from himena.consts import StandardTypes


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


@register_function(
    title="Convert table to text ...",
    types=StandardTypes.TABLE,
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
        from tabulate import tabulate

        format = format.lower()
        if format == "markdown":
            s = tabulate(model.value, tablefmt="github")
            ext_default = ".md"
            language = "markdown"
        elif format == "latex":
            s = _table_to_latex(model.value)
            ext_default = ".tex"
            language = "latex"
        elif format == "html":
            s = tabulate(model.value, tablefmt="html")
            ext_default = ".html"
            language = "html"
        elif format == "rst":
            s = tabulate(model.value, tablefmt="rst")
            ext_default = ".rst"
            language = "rst"
        elif format == "csv":
            s = "\n".join(",".join(row) for row in model.value)
            ext_default = ".csv"
            language = None
        elif format == "tsv":
            s = "\n".join("\t".join(row) for row in model.value)
            ext_default = ".tsv"
            language = None
        else:
            raise ValueError(f"Unknown format: {format}")
        return WidgetDataModel(
            value=s + end_of_text,
            type=StandardTypes.TEXT,
            title=f"{model.title} (as text)",
            extension_default=ext_default,
            additional_data=TextMeta(language=language),
        )

    return convert_table_to_text


@register_function(
    title="Convert table to DataFrame ...",
    types=StandardTypes.TABLE,
    menus=["tools/table"],
    command_id="builtins:table-to-dataframe",
)
def table_to_dataframe(model: WidgetDataModel) -> Parametric[str]:
    """Convert a table data into a DataFrame."""
    from io import StringIO

    def convert_table_to_dataframe(
        module: Literal["pandas", "polars"] = "pandas",
    ) -> WidgetDataModel[str]:
        mod = importlib.import_module(module)
        csv = "\n".join(",".join(row) for row in model.value)
        buf = StringIO(csv)
        df = mod.read_csv(buf)
        return WidgetDataModel(
            value=df,
            title=f"{model.title} (as dataframe)",
            type=StandardTypes.DATAFRAME,
        )

    return convert_table_to_dataframe


# TODO: table_to_array_2d
# TODO: table_to_image
