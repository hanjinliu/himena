import csv
from io import StringIO
import re
import html
from himena.plugins import register_function, configure_gui
from himena.types import Parametric, WidgetDataModel
from himena.model_meta import TextMeta
from himena.consts import StandardType
from himena import _utils


@register_function(
    types=StandardType.TEXT,
    menus=["tools/text"],
    keybindings="Ctrl+F5",
    command_id="builtins:run-script",
)
def run_script(model: WidgetDataModel[str]):
    """Run a Python script."""
    script = model.value
    if isinstance(model.metadata, TextMeta):
        if model.metadata.language.lower() == "python":
            exec(script)
        else:
            raise ValueError(f"Cannot run {model.metadata.language}.")
    else:
        raise ValueError("Unknown language.")
    return None


@register_function(
    types=StandardType.TEXT,
    menus=["tools/text"],
    title="Convert text to table ...",
    command_id="builtins:text-to-table",
)
def text_to_table(model: WidgetDataModel[str]) -> Parametric:
    """Convert text to a table-type widget."""

    @configure_gui(
        title="Convert text to table ...",
    )
    def run(separator: str = ",") -> WidgetDataModel:
        lines = model.value.splitlines()
        table = []
        sep = separator.encode().decode("unicode_escape")
        for line in lines:
            table.append(line.split(sep))
        return WidgetDataModel(
            value=table,
            type=StandardType.TABLE,
            title=model.title,
            extension_default=".csv",
        )

    return run


@register_function(
    types=StandardType.TEXT,
    menus=["tools/text"],
    title="Convert text to array ...",
    command_id="builtins:text-to-array",
)
def text_to_array(model: WidgetDataModel[str]) -> WidgetDataModel:
    """Convert text to an array-type widget using numpy."""
    import numpy as np
    from io import StringIO

    text = model.value
    arr = np.loadtxt(StringIO(text), delimiter=",")
    return WidgetDataModel(
        value=arr,
        type=StandardType.ARRAY,
        title=model.title,
        extension_default=".npy",
    )


@register_function(
    types=StandardType.TEXT,
    menus=["tools/text"],
    title="Convert text to DataFrame ...",
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


@register_function(
    types=StandardType.TEXT,
    menus=["tools/text"],
    command_id="builtins:text-change-separator",
)
def change_separator(model: WidgetDataModel[str]) -> Parametric:
    """Change the separator (in the sense of CSV or TSV) of a text."""

    def change_separator_data(old: str = ",", new: str = r"\t") -> WidgetDataModel[str]:
        if old == "" or new == "":
            raise ValueError("Old and new separators must not be empty.")
        # decode unicode escape. e.g., "\\t" -> "\t"
        old = old.encode().decode("unicode_escape")
        new = new.encode().decode("unicode_escape")
        buf = StringIO(model.value)
        reader = csv.reader(buf, delimiter=old)
        new_text = "\n".join(new.join(row) for row in reader)
        return WidgetDataModel(
            value=new_text,
            type=model.type,
            title=_utils.add_title_suffix(model.title),
            extensions=model.extensions,
            metadata=model.metadata,
        )

    return change_separator_data


@register_function(
    types=StandardType.TEXT,
    menus=["tools/text"],
    command_id="builtins:text-change-encoding",
)
def change_encoding(model: WidgetDataModel[str]) -> Parametric:
    """Change the encoding of a text."""

    def change_encoding_data(encoding: str = "utf-8") -> WidgetDataModel[str]:
        new_text = model.value.encode(encoding).decode(encoding)
        out = model.with_value(new_text)
        if isinstance(meta := model.metadata, TextMeta):
            meta.encoding = encoding
        return out

    return change_encoding_data


@register_function(
    types=StandardType.HTML,
    menus=["tools/html"],
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


@register_function(
    types=StandardType.HTML,
    menus=["tools/html"],
    command_id="builtins:show-in-text-editor",
    title="Show in text editor",
)
def show_in_text_editor(model: WidgetDataModel[str]) -> WidgetDataModel:
    """Show HTML directly in text editor."""
    return model.with_value(
        value=model.value,
        type=StandardType.TEXT,
        metadata=TextMeta(language="html"),
    )
