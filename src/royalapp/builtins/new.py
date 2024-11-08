"""New file actions."""

from royalapp.plugins import get_plugin_interface
from royalapp.types import WidgetDataModel, Parametric
from royalapp.widgets import MainWindow
from royalapp.consts import StandardTypes
import csv
import requests
from io import StringIO

__royalapp_plugin__ = get_plugin_interface()


@__royalapp_plugin__.register_new_provider(
    keybindings="Ctrl+N",
    command_id="builtins:new-text",
)
def new_text(ui: MainWindow) -> WidgetDataModel:
    """New text file."""
    if tab := ui.tabs.current():
        nwin = len(tab)
    else:
        nwin = 0
    return WidgetDataModel(value="", type=StandardTypes.TEXT, title=f"Untitled-{nwin}")


@__royalapp_plugin__.register_new_provider(
    title="Seaborn test data",
    command_id="builtins:fetch-seaborn-test-data",
)
def seaborn_test_data() -> Parametric:
    """New table from a seaborn test data."""

    def fetch_data(name: str = "iris") -> WidgetDataModel:
        url = (
            f"https://raw.githubusercontent.com/mwaskom/seaborn-data/master/{name}.csv"
        )

        # read without using pandas
        response = requests.get(url)
        response.raise_for_status()  # Ensure we notice bad responses

        data = response.text
        csv_data = list(csv.reader(StringIO(data)))

        return WidgetDataModel(value=csv_data, type=StandardTypes.TABLE, title=name)

    return fetch_data
