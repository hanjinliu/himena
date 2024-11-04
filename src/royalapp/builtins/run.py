"""Run actions."""

from royalapp.plugins import get_plugin_interface
from royalapp.types import WidgetDataModel, TextFileMeta
from royalapp.consts import StandardTypes

__royalapp_plugin__ = get_plugin_interface("tools")


@__royalapp_plugin__.register_function(
    types=[StandardTypes.TEXT, "text"],
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
    return WidgetDataModel(value="", type=StandardTypes.TEXT, title="Untitled")
