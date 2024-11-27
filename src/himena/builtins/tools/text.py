import importlib
from typing import Callable
import json
import csv
from io import StringIO
from himena.plugins import register_function, configure_gui
from himena.types import Parametric, WidgetDataModel
from himena.model_meta import TextMeta
from himena.consts import StandardType
from himena import _utils


@register_function(
    title="Filter text ...",
    types=StandardType.TEXT,
    menus=["tools/text"],
    preview=True,
    command_id="builtins:filter-text",
)
def filter_text(model: WidgetDataModel[str]) -> Parametric[str]:
    """Filter text by its content."""

    def filter_text_data(
        include: str = "",
        exclude: str = "",
        case_sensitive: bool = True,
    ) -> WidgetDataModel[str]:
        if include == "":
            _include = _const_func(True)
        else:
            _include = _contains_func(include, case_sensitive)
        if exclude == "":
            _exclude = _const_func(False)
        else:
            _exclude = _contains_func(exclude, case_sensitive)
        new_text = "\n".join(
            line
            for line in model.value.splitlines()
            if _include(line) and not _exclude(line)
        )
        if isinstance(model.metadata, TextMeta):
            meta = model.metadata.model_copy(update={"selection": None})
        else:
            meta = TextMeta()
        return WidgetDataModel(
            value=new_text,
            type=model.type,
            title=f"{model.title} (filtered)",
            extensions=model.extensions,
            metadata=meta,
        )

    return filter_text_data


@register_function(
    title="Format JSON ...",
    menus=["tools/text"],
    types=StandardType.TEXT,
    command_id="builtins:format-json",
)
def format_json(model: WidgetDataModel) -> Parametric:
    """Format JSON."""

    def format_json_data(indent: int = 2) -> WidgetDataModel[str]:
        if not isinstance(meta := model.metadata, TextMeta):
            meta = TextMeta()
        return WidgetDataModel(
            value=json.dumps(json.loads(model.value), indent=indent),
            type=model.type,
            title=f"{model.title} (formatted)",
            extension_default=".json",
            extensions=model.extensions,
            metadata=TextMeta(
                language="JSON",
                spaces=indent,
                selection=meta.selection,
                font_family=meta.font_family,
                font_size=meta.font_size,
            ),
        )

    return format_json_data


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
def text_to_table(model: WidgetDataModel[str]) -> WidgetDataModel:
    """Convert text to a table-type widget."""
    lines = model.value.splitlines()
    table = []
    for line in lines:
        table.append(line.split(","))
    return WidgetDataModel(
        value=table,
        type=StandardType.TABLE,
        title=model.title,
        extension_default=".csv",
    )


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
    from himena._data_wrappers import list_installed_dataframe_packages

    pkgs = ["dict"] + list_installed_dataframe_packages()

    @configure_gui(module={"choices": pkgs, "value": pkgs[0]})
    def convert_text_to_dataframe(module) -> WidgetDataModel[str]:
        mod = importlib.import_module(module)
        buf = StringIO(model.value)
        df = mod.read_csv(buf)
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
    command_id="builtins:change-separator",
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


def _const_func(x) -> Callable[[str], bool]:
    def _func(line: str):
        return x

    return _func


def _contains_func(x: str, case_sensitive: bool) -> Callable[[str], bool]:
    if case_sensitive:

        def _func(line: str):
            return x in line
    else:
        x0 = x.lower()

        def _func(line: str):
            return x0 in line.lower()

    return _func
