"""Run actions."""

from typing import Callable
import json
from himena.plugins import register_function
from himena.types import Parametric, WidgetDataModel
from himena.model_meta import TextMeta
from himena.consts import StandardTypes


@register_function(
    title="Filter text ...",
    types=StandardTypes.TEXT,
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
        if isinstance(model.additional_data, TextMeta):
            meta = model.additional_data.model_copy(update={"selection": None})
        else:
            meta = TextMeta()
        return WidgetDataModel(
            value=new_text,
            type=model.type,
            title=f"{model.title} (filtered)",
            extensions=model.extensions,
            additional_data=meta,
        )

    return filter_text_data


@register_function(
    title="Format JSON ...",
    menus=["tools/text"],
    types=StandardTypes.TEXT,
    command_id="builtins:format-json",
)
def format_json(model: WidgetDataModel) -> Parametric:
    """Format JSON."""

    def format_json_data(indent: int = 2) -> WidgetDataModel[str]:
        if not isinstance(meta := model.additional_data, TextMeta):
            meta = TextMeta()
        return WidgetDataModel(
            value=json.dumps(json.loads(model.value), indent=indent),
            type=model.type,
            title=f"{model.title} (formatted)",
            extension_default=".json",
            extensions=model.extensions,
            additional_data=TextMeta(
                language="JSON",
                spaces=indent,
                selection=meta.selection,
                font_family=meta.font_family,
                font_size=meta.font_size,
            ),
        )

    return format_json_data


@register_function(
    types=StandardTypes.TEXT,
    menus=["tools/text"],
    keybindings="Ctrl+F5",
)
def run_script(model: WidgetDataModel[str]):
    """Run a Python script."""
    script = model.value
    if isinstance(model.additional_data, TextMeta):
        if model.additional_data.language.lower() == "python":
            exec(script)
        else:
            raise ValueError(f"Cannot run {model.additional_data.language}.")
    else:
        raise ValueError("Unknown language.")
    return None


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
