"""New file actions."""

import csv
from io import StringIO

from himena.plugins import register_function, configure_gui
from himena.types import WidgetDataModel, Parametric
from himena.widgets import MainWindow
from himena.consts import StandardType, MenuId


def _get_n_windows(ui: MainWindow) -> int:
    if tab := ui.tabs.current():
        return len(tab)
    return 0


@register_function(menus=MenuId.FILE_NEW, command_id="builtins:new-text")
def new_text(ui: MainWindow) -> WidgetDataModel:
    """New text file."""
    nwin = _get_n_windows(ui)
    return WidgetDataModel(
        value="",
        type=StandardType.TEXT,
        extension_default=".txt",
        title=f"Untitled-{nwin}",
    )


@register_function(menus=MenuId.FILE_NEW, command_id="builtins:new-table")
def new_table(ui: MainWindow) -> WidgetDataModel:
    """New table."""
    nwin = _get_n_windows(ui)
    return WidgetDataModel(
        value=None,
        type=StandardType.TABLE,
        extension_default=".csv",
        title=f"Table-{nwin}",
    )


@register_function(menus=MenuId.FILE_NEW, command_id="builtins:new-excel")
def new_excel(ui: MainWindow) -> WidgetDataModel:
    """New table."""
    nwin = _get_n_windows(ui)
    return WidgetDataModel(
        value={"Sheet-1": None},
        type=StandardType.EXCEL,
        extension_default=".xlsx",
        title=f"Excel-{nwin}",
    )


@register_function(menus=MenuId.FILE_NEW, command_id="builtins:new-draw-canvas")
def new_draw_canvas(ui: MainWindow) -> WidgetDataModel:
    """New draw canvas."""
    nwin = _get_n_windows(ui)
    return WidgetDataModel(
        value=None,
        type=StandardType.IMAGE,
        extension_default=".png",
        title=f"Canvas-{nwin}",
        force_open_with="builtins:QDrawCanvas",
    )


DATASET_SOURCE = "https://raw.githubusercontent.com/mwaskom/seaborn-data/master"
DATASET_NAMES_URL = f"{DATASET_SOURCE}/dataset_names.txt"


@register_function(
    title="Seaborn sample data ...",
    menus=MenuId.FILE_SAMPLES,
    command_id="builtins:fetch-seaborn-sample-data",
)
def seaborn_sample_data() -> Parametric:
    """New table from a seaborn test data."""
    from urllib.request import urlopen

    # get dataset names
    with urlopen(DATASET_NAMES_URL) as resp:
        txt = resp.read()

    assert isinstance(txt, bytes)
    dataset_names = [name.strip() for name in txt.decode().split("\n")]
    choices = [name for name in dataset_names if name]

    @configure_gui(
        name={"choices": choices},
        title="Choose a dataset ...",
        show_parameter_labels=False,
    )
    def fetch_data(name: str = "iris") -> WidgetDataModel:
        # read without using pandas
        with urlopen(f"{DATASET_SOURCE}/{name}.csv") as resp:
            data = resp.read().decode()

        csv_data = list(csv.reader(StringIO(data)))
        return WidgetDataModel(value=csv_data, type=StandardType.TABLE, title=name)

    return fetch_data


@register_function(
    title="Constant array ...",
    menus=MenuId.FILE_NEW,
    command_id="builtins:constant-array",
)
def constant_array(ui: MainWindow) -> Parametric:
    """Generate an array filled with a constant value."""
    import numpy as np
    from himena.qt._magicgui import NumericDTypeEdit
    from himena.plugins import configure_gui

    @configure_gui(dtype={"widget_type": NumericDTypeEdit})
    def generate_constant_array(
        shape: list[int] = (256, 256),
        dtype="uint8",
        value: str = "0",
        interpret_as_image: bool = False,
    ):
        _dtype = np.dtype(dtype)
        if _dtype.kind == "f":
            _value = float(value)
        elif _dtype.kind in "iu":
            _value = int(value)
        elif _dtype.kind == "b":
            _value = bool(value)
        elif _dtype.kind == "c":
            _value = complex(value)
        else:
            _value = value
        arr = np.full(shape, _value, dtype=dtype)
        if interpret_as_image:
            type = StandardType.IMAGE
        else:
            type = StandardType.ARRAY
        nwin = _get_n_windows(ui)
        return WidgetDataModel(value=arr, type=type, title=f"Untitled-{nwin}")

    return generate_constant_array
