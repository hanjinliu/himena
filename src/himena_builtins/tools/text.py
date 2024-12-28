import csv
from io import StringIO
from himena.plugins import register_function
from himena.types import Parametric, WidgetDataModel
from himena.standards.model_meta import TextMeta
from himena.consts import StandardType


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
            extensions=model.extensions,
            metadata=model.metadata,
        ).with_title_numbering()

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
