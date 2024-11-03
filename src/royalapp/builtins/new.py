"""New file actions."""

from royalapp.plugins import get_plugin_interface
from royalapp.types import WidgetDataModel
from royalapp.consts import StandardTypes

__royalapp_plugin__ = get_plugin_interface()


@__royalapp_plugin__.register_new_provider(keybindings="Ctrl+N")
def new_text() -> WidgetDataModel:
    """Create widget for a new text file."""
    return WidgetDataModel(value="", type=StandardTypes.TEXT, title="New Text Window")
