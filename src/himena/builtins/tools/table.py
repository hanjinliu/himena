from io import StringIO
import numpy as np

from himena.plugins import register_function, configure_gui
from himena.types import Parametric, WidgetDataModel
from himena.standards.model_meta import TableMeta
from himena.consts import StandardType


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
