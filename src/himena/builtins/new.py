"""New file actions."""

from typing import Literal
import csv
from io import StringIO

from himena.plugins import register_new_provider, configure_gui
from himena.types import WidgetDataModel, Parametric
from himena.widgets import MainWindow
from himena.consts import StandardTypes


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


DATASET_SOURCE = "https://raw.githubusercontent.com/mwaskom/seaborn-data/master"
DATASET_NAMES_URL = f"{DATASET_SOURCE}/dataset_names.txt"


@register_new_provider(
    title="Seaborn test data",
    command_id="builtins:fetch-seaborn-test-data",
)
def seaborn_test_data() -> Parametric:
    """New table from a seaborn test data."""
    from urllib.request import urlopen

    # get dataset names
    with urlopen(DATASET_NAMES_URL) as resp:
        txt = resp.read()

    assert isinstance(txt, bytes)
    dataset_names = [name.strip() for name in txt.decode().split("\n")]
    choices = [name for name in dataset_names if name]

    @configure_gui(name={"choices": choices})
    def fetch_data(name: str = "iris") -> WidgetDataModel:
        # read without using pandas
        with urlopen(f"{DATASET_SOURCE}/{name}.csv") as resp:
            data = resp.read().decode()

        csv_data = list(csv.reader(StringIO(data)))
        return WidgetDataModel(value=csv_data, type=StandardTypes.TABLE, title=name)

    return fetch_data


@register_new_provider(
    title="Random image ...",
    command_id="builtins:random-image",
)
def random_image() -> Parametric:
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
