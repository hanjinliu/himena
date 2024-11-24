from typing import TYPE_CHECKING
from himena.plugins import register_function, configure_gui
from himena.types import Parametric, WidgetDataModel
from himena.consts import StandardType
from himena.widgets import SubWindow
from himena.model_meta import ExcelMeta, TableMeta
from himena.qt._magicgui import SelectionEdit
from himena import plotting
from himena.exceptions import DeadSubwindowError

if TYPE_CHECKING:
    import numpy as np


@register_function(
    title="Scatter plot ...",
    types=[
        StandardType.TABLE,
        StandardType.DATAFRAME,
        StandardType.EXCEL,
    ],
    command_id="builtins:scatter-plot",
)
def scatter_plot(win: SubWindow) -> Parametric:
    def range_getter():
        if not win.is_alive:
            raise DeadSubwindowError("Subwindow is already removed.")
        model = win.to_model()
        types = [StandardType.TABLE, StandardType.DATAFRAME, StandardType.EXCEL]
        if model.type not in types:
            raise ValueError(f"Cannot plot model of type {model.type!r}")
        if not isinstance(meta := model.additional_data, TableMeta):
            raise ValueError("Excel must have TableMeta as the additional data.")

        if len(meta.selections) == 0:
            raise ValueError(f"No selection found in window {win.title!r}")
        elif len(meta.selections) > 1:
            raise ValueError(f"More than one selection found in window {win.title!r}")
        sel = meta.selections[0]
        # TODO: thoroughly check the type.
        rindices, cindices = sel
        rsl = slice(*rindices)
        csl = slice(*cindices)
        return rsl, csl

    @configure_gui(
        x={"widget_type": SelectionEdit, "getter": range_getter},
        y={"widget_type": SelectionEdit, "getter": range_getter},
    )
    def configure_plot(
        x: tuple[slice, slice] | None,
        y: tuple[slice, slice],
    ) -> WidgetDataModel:
        fig = plotting.figure()
        xarr, yarrs = _get_xy_data(win, x, y, fig.axes)
        for yarr in yarrs:
            fig.axes.scatter(xarr, yarr)
        return WidgetDataModel(value=fig, type=StandardType.PLOT)

    return configure_plot


def _get_xy_data(
    win: SubWindow,
    x: tuple[slice, slice] | None,
    y: tuple[slice, slice] | None,
    axes: plotting.layout.Axes,
) -> "tuple[np.ndarray, list[np.ndarray]]":
    import numpy as np
    from himena._data_wrappers import wrap_dataframe

    model = win.to_model()
    if model.type == StandardType.TABLE:
        xarr, yarrs = _table_to_xy_data(model.value, x, y, axes)
    elif model.type == StandardType.DATAFRAME:
        df = wrap_dataframe(model.value)
        column_names = df.column_names()[y[1].start, y[1].stop]
        rows = slice(y[0].start, y[0].stop)
        yarrs = [df.column_to_array(cname)[rows] for cname in column_names]
        if x is None:
            xarr = np.arange(yarrs[0].size)
        else:
            column_names_x = df.column_names()[x[1].start, x[1].stop]
            if len(column_names_x) != 1:
                raise ValueError("x must not be more than one column.")
            xarr = df.column_to_array(column_names_x[0])
            axes.x.label = column_names_x[0]
        axes.y.label = df.column_names()[y[0].start]
    elif model.type == StandardType.EXCEL:
        if not isinstance(meta := model.additional_data, ExcelMeta):
            raise ValueError("Must be a ExcelMeta")
        table = model.value[meta.current_sheet]
        xarr, yarrs = _table_to_xy_data(table, x, y, axes)
    else:
        raise RuntimeError("Unreachable")
    return xarr, yarrs


def _table_to_xy_data(
    value: "np.ndarray",
    x: tuple[slice, slice] | None,
    y: tuple[slice, slice],
    axes: plotting.layout.Axes,
) -> "tuple[np.ndarray, list[np.ndarray]]":
    import numpy as np

    yarr = np.asarray(value[y], dtype=np.float64)
    if x is None:
        xarr = np.arange(yarr.shape[0], dtype=np.float64)
    else:
        xarr = value[x]
        if xarr.shape[0] == 1:
            if xarr.shape[1] != yarr.shape[1]:
                raise ValueError("Shape mismatch")
            yarrs = list(yarr)
        elif xarr.shape[1] == 1:
            if xarr.shape[0] != yarr.shape[0]:
                raise ValueError("Shape mismatch")
            yarrs = list(yarr.T)
        else:
            raise ValueError("x must be 1D selection")

        xarr = xarr.ravel()
        try:
            xarr = np.asarray(xarr, dtype=np.float64)
        except Exception:
            # X values are not numerical. Label them at 0, 1, 2, ...
            axes.x.ticks = [str(a) for a in xarr]
            xarr = np.arange(xarr.size, dtype=np.float64)
    return xarr, yarrs
