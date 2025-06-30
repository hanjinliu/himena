from io import StringIO
from typing import TYPE_CHECKING
import numpy as np
from himena.plugins import register_function, configure_gui, configure_submenu
from himena.types import ClipboardDataModel, Parametric, WidgetDataModel
from himena.standards.model_meta import TableMeta
from himena.consts import StandardType, MenuId
from himena.utils.misc import table_to_text
from himena.widgets import SubWindow

if TYPE_CHECKING:
    from himena_builtins.qt.widgets.table import QSpreadsheet

configure_submenu(MenuId.TOOLS_TABLE, group="20_builtins", order=1)


@register_function(
    title="Crop Selection",
    types=StandardType.TABLE,
    menus=[MenuId.TOOLS_TABLE],
    command_id="builtins:table:crop",
)
def crop_selection(model: WidgetDataModel["np.ndarray"]) -> Parametric:
    """Crop the table data at the selection."""

    @configure_gui(selection={"bind": lambda *_: _get_selection(model)})
    def run_crop_selection(
        selection: tuple[tuple[int, int], tuple[int, int]],
    ) -> WidgetDataModel:
        (r0, r1), (c0, c1) = selection
        arr_str = model.value
        arr_new = arr_str[r0:r1, c0:c1]
        out = model.with_value(arr_new)
        if isinstance(meta := out.metadata, TableMeta):
            meta.selections = []
        return out

    return run_crop_selection


@register_function(
    title="Change Separator ...",
    types=StandardType.TABLE,
    menus=[MenuId.TOOLS_TABLE],
    command_id="builtins:table:change-separator",
)
def change_separator(model: WidgetDataModel) -> Parametric:
    """Change the separator of the table data."""
    arr_str = model.value
    meta = _cast_meta(model.metadata)
    sep = meta.separator
    if sep is None:
        raise ValueError("Current separator of the table is unknown.")

    def change_separator(separator: str = ",") -> None:
        buf = _arr_to_buf(arr_str, sep)
        arr_new = np.loadtxt(
            buf,
            delimiter=separator.encode().decode("unicode_escape"),
            dtype=np.dtypes.StringDType(),
        )
        meta = _cast_meta(model.metadata)
        meta.separator = separator
        return model.with_value(arr_new, metadata=meta, update_inplace=True)

    return change_separator


@register_function(
    title="Copy as CSV",
    types=StandardType.TABLE,
    menus=[MenuId.TOOLS_TABLE_COPY, "/model_menu/copy"],
    command_id="builtins:table:copy-as-csv",
)
def copy_as_csv(model: WidgetDataModel) -> ClipboardDataModel:
    """Copy the table data as CSV format."""
    return _to_clipboard_data_model(model, "CSV")


@register_function(
    title="Copy as Markdown",
    types=StandardType.TABLE,
    menus=[MenuId.TOOLS_TABLE_COPY, "/model_menu/copy"],
    command_id="builtins:table:copy-as-markdown",
)
def copy_as_markdown(model: WidgetDataModel) -> ClipboardDataModel:
    """Copy the table data as Markdown format."""
    return _to_clipboard_data_model(model, "Markdown")


@register_function(
    title="Copy as HTML",
    types=StandardType.TABLE,
    menus=[MenuId.TOOLS_TABLE_COPY, "/model_menu/copy"],
    command_id="builtins:table:copy-as-html",
)
def copy_as_html(model: WidgetDataModel) -> ClipboardDataModel:
    """Copy the table data as HTML format."""
    return _to_clipboard_data_model(model, "HTML")


@register_function(
    title="Copy as rST",
    types=StandardType.TABLE,
    menus=[MenuId.TOOLS_TABLE_COPY, "/model_menu/copy"],
    command_id="builtins:table:copy-as-rst",
)
def copy_as_rst(model: WidgetDataModel) -> ClipboardDataModel:
    """Copy the table data as reStructuredText format."""
    return _to_clipboard_data_model(model, "rST")


@register_function(
    title="Insert Incrementing Numbers",
    types=StandardType.TABLE,
    menus=[MenuId.TOOLS_TABLE],
    command_id="builtins:table:insert-incrementing-numbers",
)
def insert_incrementing_numbers(win: SubWindow["QSpreadsheet"]) -> Parametric:
    """Insert incrementing numbers (0, 1, 2, ...) in-place to the selected range."""
    widget = win.widget

    def _get_selection(*_):
        meta = _cast_meta(win.to_model().metadata)
        sels = meta.selections
        if sels is None or len(sels) != 1:
            raise ValueError("Table must contain single selection to crop.")
        return sels[0]

    @configure_gui(title="Change separator", selection={"bind": _get_selection})
    def run_insert(
        selection: tuple[tuple[int, int], tuple[int, int]],
        start: int = 0,
        step: int = 1,
    ) -> None:
        (r0, r1), (c0, c1) = selection
        length = (r1 - r0) * (c1 - c0)
        values = [str(i) for i in range(start, start + length * step, step)]
        if r1 - r0 != 1 and c1 - c0 != 1:
            raise ValueError("Select a single row or column.")
        nr, nc = widget.model()._arr.shape
        if nr < r1 or nc < c1:
            widget.array_expand(r1, c1)
        target = widget.model()._arr
        if r1 - r0 == 1:
            target[r0:r1, c0:c1] = np.array(values, dtype=target.dtype).reshape(1, -1)
        else:
            target[r0:r1, c0:c1] = np.array(values, dtype=target.dtype).reshape(-1, 1)
        return

    return run_insert


def _cast_meta(meta) -> TableMeta:
    if not isinstance(meta, TableMeta):
        raise ValueError("Table must have a TableMeta as the metadata")
    return meta


def _arr_to_buf(arr: "np.ndarray", sep: str = ",") -> StringIO:
    buf = StringIO()
    np.savetxt(buf, arr, fmt="%s", delimiter=sep)
    buf.seek(0)
    return buf


def _get_selection(
    model: WidgetDataModel["np.ndarray"],
    allow_no_selection: bool = False,
) -> tuple[tuple[int, int], tuple[int, int]]:
    meta = _cast_meta(model.metadata)
    sels = meta.selections
    if sels is None or len(sels) == 0:
        if allow_no_selection:
            nr, nc = model.value.shape
            return (0, nr), (0, nc)
        raise ValueError("Table has no selection.")
    if len(sels) != 1:
        raise ValueError("Table must not contain multiple selections.")
    return sels[0]


def _to_clipboard_data_model(model: WidgetDataModel, format: str) -> ClipboardDataModel:
    (r0, r1), (c0, c1) = _get_selection(model, allow_no_selection=True)
    string, _, _ = table_to_text(model.value[r0:r1, c0:c1], format=format)
    return ClipboardDataModel(text=string)
