"""Run actions."""

from himena.plugins import get_plugin_interface
from himena.types import WidgetDataModel, TextFileMeta
from himena.consts import StandardTypes

__himena_plugin__ = get_plugin_interface("tools")


@__himena_plugin__.register_function(
    types=StandardTypes.TEXT,
    keybindings="Ctrl+F5",
)
def run_script(model: WidgetDataModel[str]):
    """Run a Python script."""
    script = model.value
    if isinstance(model.additional_data, TextFileMeta):
        if model.additional_data.language.lower() == "python":
            exec(script)
        else:
            raise ValueError(f"Cannot run {model.additional_data.language}.")
    else:
        raise ValueError("Unknown language.")
    return None
