from typing import TYPE_CHECKING, Iterator
import itertools

from cmap import Color, Colormap
import numpy as np

from himena.plugins import register_function, configure_gui
from himena.types import Parametric, WidgetDataModel
from himena.consts import StandardType
from himena.widgets import SubWindow
from himena.model_meta import ExcelMeta, TableMeta
from himena.plotting import layout
from himena.qt._magicgui import SelectionEdit, FacePropertyEdit, EdgePropertyEdit
from himena import plotting
from himena.exceptions import DeadSubwindowError

if TYPE_CHECKING:
    from himena.qt._magicgui._face_edge import FacePropertyDict, EdgePropertyDict

_TABLE_LIKE = [StandardType.TABLE, StandardType.DATAFRAME, StandardType.EXCEL]
_MENU = "tools/plot"


@register_function(
    title="Scatter plot ...",
    types=_TABLE_LIKE,
    menus=_MENU,
    command_id="builtins:scatter-plot",
)
def scatter_plot(win: SubWindow) -> Parametric:
    @configure_gui(
        x={"widget_type": SelectionEdit, "getter": lambda: _range_getter(win)},
        y={"widget_type": SelectionEdit, "getter": lambda: _range_getter(win)},
        face={"widget_type": FacePropertyEdit},
        edge={"widget_type": EdgePropertyEdit},
    )
    def configure_plot(
        x: tuple[slice, slice] | None,
        y: tuple[slice, slice],
        symbol: str = "o",
        size: float = 6.0,
        face: dict = {},
        edge: dict = {},
    ) -> WidgetDataModel:
        fig = plotting.figure()
        xarr, yarrs = _get_xy_data(win, x, y, fig.axes)
        for yarr, _face, _edge in zip(
            yarrs, _iter_face(face), _iter_edge(edge, prefix="edge_")
        ):
            fig.axes.scatter(xarr, yarr, symbol=symbol, size=size, **_face, **_edge)
        return WidgetDataModel(value=fig, type=StandardType.PLOT)

    return configure_plot


@register_function(
    title="Line plot ...",
    types=_TABLE_LIKE,
    menus=_MENU,
    command_id="builtins:line-plot",
)
def line_plot(win: SubWindow) -> Parametric:
    @configure_gui(
        x={"widget_type": SelectionEdit, "getter": lambda: _range_getter(win)},
        y={"widget_type": SelectionEdit, "getter": lambda: _range_getter(win)},
        edge={"widget_type": EdgePropertyEdit},
    )
    def configure_plot(
        x: tuple[slice, slice] | None,
        y: tuple[slice, slice],
        edge: dict = {},
    ) -> WidgetDataModel:
        fig = plotting.figure()
        xarr, yarrs = _get_xy_data(win, x, y, fig.axes)
        for yarr, _edge in zip(yarrs, _iter_edge(edge)):
            fig.axes.plot(xarr, yarr, **_edge)
        return WidgetDataModel(value=fig, type=StandardType.PLOT)

    return configure_plot


@register_function(
    title="Bar plot ...",
    types=_TABLE_LIKE,
    menus=_MENU,
    command_id="builtins:bar-plot",
)
def bar_plot(win: SubWindow) -> Parametric:
    @configure_gui(
        x={"widget_type": SelectionEdit, "getter": lambda: _range_getter(win)},
        y={"widget_type": SelectionEdit, "getter": lambda: _range_getter(win)},
        bottom={"widget_type": SelectionEdit, "getter": lambda: _range_getter(win)},
        face={"widget_type": FacePropertyEdit},
        edge={"widget_type": EdgePropertyEdit},
    )
    def configure_plot(
        x: tuple[slice, slice] | None,
        y: tuple[slice, slice],
        bottom: tuple[slice, slice] | None = None,
        bar_width: float = 0.8,
        face: dict = {},
        edge: dict = {},
    ) -> WidgetDataModel:
        fig = plotting.figure()
        if bottom is not None:
            _, bottoms = _get_xy_data(win, x, bottom, fig.axes)
        else:
            bottoms = itertools.repeat(None)
        xarr, yarrs = _get_xy_data(win, x, y, fig.axes)
        for yarr, _bottom, _face, _edge in zip(
            yarrs, bottoms, _iter_face(face), _iter_edge(edge, prefix="edge_")
        ):
            fig.axes.bar(
                xarr, yarr, bottom=_bottom, bar_width=bar_width, **_face, **_edge
            )
        return WidgetDataModel(value=fig, type=StandardType.PLOT)

    return configure_plot


@register_function(
    title="Errorbar plot ...",
    types=_TABLE_LIKE,
    menus=_MENU,
    command_id="builtins:errorbar-plot",
)
def errorbar_plot(win: SubWindow) -> Parametric:
    @configure_gui(
        x={"widget_type": SelectionEdit, "getter": lambda: _range_getter(win)},
        y={"widget_type": SelectionEdit, "getter": lambda: _range_getter(win)},
        xerr={"widget_type": SelectionEdit, "getter": lambda: _range_getter(win)},
        yerr={"widget_type": SelectionEdit, "getter": lambda: _range_getter(win)},
        edge={"widget_type": EdgePropertyEdit},
    )
    def configure_plot(
        x: tuple[slice, slice] | None,
        y: tuple[slice, slice],
        xerr: tuple[slice, slice] | None,
        yerr: tuple[slice, slice] | None,
        capsize: float = 0.0,
        edge: dict = {},
    ) -> WidgetDataModel:
        fig = plotting.figure()
        if xerr is not None:
            _, xerrs = _get_xy_data(win, x, xerr, fig.axes)
        else:
            xerrs = itertools.repeat(None)
        if yerr is not None:
            _, yerrs = _get_xy_data(win, x, yerr, fig.axes)
        else:
            yerrs = itertools.repeat(None)
        xarr, yarrs = _get_xy_data(win, x, y, fig.axes)
        for yarr, _xerr, _yerr, _edge in zip(yarrs, xerrs, yerrs, _iter_edge(edge)):
            fig.axes.errorbar(
                xarr, yarr, x_error=_xerr, y_error=_yerr, capsize=capsize, **_edge
            )
        return WidgetDataModel(value=fig, type=StandardType.PLOT)

    return configure_plot


@register_function(
    title="Edit plot ...",
    types=[StandardType.PLOT],
    menus=_MENU,
    command_id="builtins:edit-plot",
)
def edit_plot(win: SubWindow) -> Parametric:
    model = win.to_model()
    if not isinstance(lo := model.value, layout.BaseLayoutModel):
        raise ValueError("Invalid layout model")
    if isinstance(lo, layout.SingleAxes):
        pass
    # TODO


def _range_getter(win: SubWindow):
    """The getter function for SelectionEdit"""
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


def _get_xy_data(
    win: SubWindow,
    x: tuple[slice, slice] | None,
    y: tuple[slice, slice] | None,
    axes: plotting.layout.Axes,
) -> "tuple[np.ndarray, list[np.ndarray]]":
    from himena._data_wrappers import wrap_dataframe

    if y is None:
        raise ValueError("The y value must be given.")
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
    # TODO: if the first value is string, use it as labels.
    yarr = np.asarray(value[y], dtype=np.float64)
    if x is None:
        xarr = np.arange(yarr.shape[0], dtype=np.float64)
        yarrs = list(yarr.T)
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


def _iter_face(face: "FacePropertyDict", prefix: str = "") -> Iterator[dict]:
    color = face.get("color", None)
    hatch = face.get("hatch", None)
    if isinstance(color, Colormap):
        cycler = itertools.cycle(color.color_stops.colors)
    else:
        cycler = itertools.repeat(Color(color))
    while True:
        yield {f"{prefix}color": next(cycler), f"{prefix}hatch": hatch}


def _iter_edge(edge: "EdgePropertyDict", prefix: str = "") -> Iterator[dict]:
    color = edge.get("color", None)
    width = edge.get("width", None)
    style = edge.get("style", None)
    if isinstance(color, Colormap):
        cycler = itertools.cycle(color.color_stops.colors)
    else:
        cycler = itertools.repeat(Color(color))
    while True:
        yield {
            f"{prefix}color": next(cycler),
            f"{prefix}width": width,
            f"{prefix}style": style,
        }
