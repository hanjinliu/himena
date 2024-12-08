from io import StringIO
import numpy as np

from himena.plugins import register_function, configure_gui
from himena.types import Parametric, WidgetDataModel
from himena.standards.model_meta import TableMeta
from himena.consts import StandardType
from himena.widgets import SubWindow
from himena.builtins.qt.widgets import QSpreadsheet


@register_function(
    title="Crop selection",
    types=StandardType.TABLE,
    menus=["tools/table"],
    command_id="builtins:crop-selection",
)
def crop_selection(model: WidgetDataModel["np.ndarray"]) -> WidgetDataModel:
    """Crop the table data at the selection."""
    arr_str = model.value
    if isinstance(meta := model.metadata, TableMeta):
        sels = meta.selections
        if sels is None or len(sels) != 1:
            raise ValueError("Table must contain single selection to crop.")
        (r0, r1), (c0, c1) = sels[0]
        arr_new = arr_str[r0:r1, c0:c1]
        out = model.with_value(arr_new)
        if isinstance(meta := out.metadata, TableMeta):
            meta.selections = []
        return out
    raise ValueError("Table must have a TableMeta as the metadata")


@register_function(
    title="Change separator ...",
    types=StandardType.TABLE,
    menus=["tools/table"],
    command_id="builtins:table-change-separator",
)
def change_separator(model: WidgetDataModel["np.ndarray"]) -> Parametric:
    """Change the separator of the table data."""
    arr_str = model.value
    if not isinstance(meta := model.metadata, TableMeta):
        raise ValueError("Table must have a TableMeta as the metadata")
    sep = meta.separator
    if sep is None:
        raise ValueError("Current separator of the table is unknown.")

    @configure_gui(
        title="Change separator",
        preview=True,
    )
    def change_separator(separator: str = ",") -> WidgetDataModel:
        buf = StringIO()
        np.savetxt(buf, arr_str, fmt="%s", delimiter=sep)
        buf.seek(0)
        arr_new = np.loadtxt(
            buf,
            delimiter=separator.encode().decode("unicode_escape"),
            dtype=np.dtypes.StringDType(),
        )
        return model.with_value(arr_new)

    return change_separator


@register_function(
    title="Insert incrementing numbers",
    types=StandardType.TABLE,
    menus=["tools/table"],
    command_id="builtins:insert-incrementing-numbers",
)
def insert_incrementing_numbers(win: SubWindow[QSpreadsheet]) -> Parametric:
    """Insert incrementing numbers (0, 1, 2, ...) in-place to the selected range."""
    widget = win.widget

    @configure_gui(title="Change separator")
    def run_insert(
        start: int = 0,
        step: int = 1,
    ) -> None:
        rngs = widget.selection_model.ranges
        if len(rngs) != 1:
            raise ValueError("Select a single range to insert incrementing numbers.")
        rsl, csl = rngs[0]
        length = (rsl.stop - rsl.start) * (csl.stop - csl.start)
        values = [str(i) for i in range(start, start + length, step)]
        if rsl.stop - rsl.start != 1 and csl.stop - csl.start != 1:
            raise ValueError("Select a single row or column.")
        nr, nc = widget.model()._arr.shape
        if nr < rsl.stop or nc < csl.stop:
            widget.model()._expand_array(rsl.stop, csl.stop)
        target = widget.model()._arr
        if rsl.stop - rsl.start == 1:
            target[rsl, csl] = np.array(values, dtype=target.dtype).reshape(1, -1)
        else:
            target[rsl, csl] = np.array(values, dtype=target.dtype).reshape(-1, 1)
        return

    return run_insert
