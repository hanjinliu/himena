"""Run actions."""

from himena.plugins import register_function
from himena.types import WidgetDataModel
from himena.model_meta import TextMeta
from himena.consts import StandardTypes, MenuId


@register_function(
    types=StandardTypes.TEXT,
    menus=[MenuId.TOOLS_TEXT],
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
