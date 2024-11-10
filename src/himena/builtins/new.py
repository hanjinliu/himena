"""New file actions."""

from typing import Literal
from himena.plugins import register_new_provider
from himena.types import WidgetDataModel, Parametric
from himena.widgets import MainWindow
from himena.consts import StandardTypes
import csv
import requests
from io import StringIO


@register_new_provider(
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


@register_new_provider(
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


@register_new_provider(
    command_id="builtins:random-image",
)
def random_image(ui: MainWindow) -> Parametric:
    """Generate an random image."""

    def generate_random_image(
        shape: list[int] = (256, 256),
        distribution: Literal["uniform", "normal"] = "uniform",
        seed: int | None = None,
    ):
        import numpy as np

        rng = np.random.default_rng(seed)

        if distribution == "uniform":
            image = rng.integers(0, 256, shape, dtype=np.uint8)
        elif distribution == "normal":
            image = rng.normal(0, 1, shape).astype(np.float32)
        else:
            raise ValueError(f"Invalid distribution: {distribution}")
        return WidgetDataModel(value=image, type=StandardTypes.IMAGE)

    return generate_random_image
