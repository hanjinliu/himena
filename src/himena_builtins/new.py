"""New file actions."""

import csv
from io import StringIO

from himena._descriptors import NoNeedToSave
from himena.plugins import register_function, configure_gui
from himena.standards.model_meta import TextMeta
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
        save_behavior_override=NoNeedToSave(),
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
        save_behavior_override=NoNeedToSave(),
    )


@register_function(menus=MenuId.FILE_NEW, command_id="builtins:new-excel")
def new_excel(ui: MainWindow) -> WidgetDataModel:
    """New Excel book."""
    nwin = _get_n_windows(ui)
    return WidgetDataModel(
        value={"Sheet-1": None},
        type=StandardType.EXCEL,
        extension_default=".xlsx",
        title=f"Book-{nwin}",
        save_behavior_override=NoNeedToSave(),
    )


@register_function(
    title="New Text (Python)",
    menus=MenuId.FILE_NEW,
    command_id="builtins:new-text-python",
)
def new_text_python(ui: MainWindow) -> WidgetDataModel:
    """New text file with language set to Python."""
    nwin = _get_n_windows(ui)
    return WidgetDataModel(
        value="",
        type=StandardType.TEXT,
        extension_default=".py",
        title=f"Untitled-{nwin}",
        save_behavior_override=NoNeedToSave(),
        metadata=TextMeta(language="python"),
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
        force_open_with="himena_builtins.qt.widgets.draw.QDrawCanvas",
        save_behavior_override=NoNeedToSave(),
    )


@register_function(
    title="New constant array ...",
    menus=MenuId.FILE_NEW,
    command_id="builtins:constant-array",
)
def constant_array(ui: MainWindow) -> Parametric:
    """Generate an array filled with a constant value."""
    import numpy as np
    from himena.qt.magicgui import NumericDTypeEdit

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
        return WidgetDataModel(
            value=arr,
            type=type,
            title=f"Untitled-{nwin}",
            save_behavior_override=NoNeedToSave(),
        )

    return generate_constant_array


@register_function(
    title="Define a function ...",
    menus=MenuId.FILE_NEW,
    command_id="builtins:define-function",
)
def define_function() -> WidgetDataModel:
    """Define a Python function."""
    code = "def main():\n    pass"
    return WidgetDataModel(value=code, type=StandardType.FUNCTION, title="Function")


### Seaborn sample data ###

_DATASET_SOURCE = "https://raw.githubusercontent.com/mwaskom/seaborn-data/master"
_SEABORN_SAMPLE_NAMES = [
    "anagrams", "anscombe", "attention", "brain_networks", "car_crashes", "diamonds",
    "dots", "dowjones", "exercise", "flights", "fmri", "geyser", "glue", "healthexp",
    "iris", "mpg", "penguins", "planets", "seaice", "taxis", "tips", "titanic",
]  # fmt: skip


def _make_provider(name: str):
    def fetch_sample_data() -> WidgetDataModel:
        from urllib.request import urlopen

        # read without using pandas
        with urlopen(f"{_DATASET_SOURCE}/{name}.csv", timeout=12) as resp:
            data = resp.read().decode()

        csv_data = list(csv.reader(StringIO(data)))
        return WidgetDataModel(
            value=csv_data,
            type=StandardType.TABLE,
            title=name,
            save_behavior_override=NoNeedToSave(),
        )

    fetch_sample_data.__name__ = name
    return fetch_sample_data


for seaborn_sample_name in _SEABORN_SAMPLE_NAMES:
    register_function(
        _make_provider(seaborn_sample_name),
        title=seaborn_sample_name,
        menus="file/new/seaborn",
        run_async=True,
        command_id=f"builtins:seaborn-sample:{seaborn_sample_name}",
    )
