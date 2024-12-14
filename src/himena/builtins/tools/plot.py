from typing import TYPE_CHECKING, Iterator
import itertools

from cmap import Color, Colormap
import numpy as np

from himena.plugins import register_function, configure_gui
from himena.types import Parametric, WidgetDataModel, is_subtype
from himena.consts import StandardType
from himena.widgets import SubWindow
from himena.standards.model_meta import ExcelMeta, TableMeta
from himena.standards import plotting as hplt
from himena.qt._magicgui import SelectionEdit, FacePropertyEdit, EdgePropertyEdit
from himena.exceptions import DeadSubwindowError

if TYPE_CHECKING:
    from numpy.typing import NDArray
    from himena.qt._magicgui._face_edge import FacePropertyDict, EdgePropertyDict

_TABLE_LIKE = [StandardType.TABLE, StandardType.DATAFRAME, StandardType.EXCEL]
_MENU = ["tools/plot", "/model_menu/plot"]
_EDGE_ONLY_VALUE = {"color": "tab10", "width": 2.0}


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
        fig = hplt.figure()
        xarr, yarrs = _get_xy_data(win, x, y, fig.axes)
        for name_yarr, _face, _edge in zip(
            yarrs, _iter_face(face), _iter_edge(edge, prefix="edge_")
        ):
            name, yarr = name_yarr
            fig.axes.scatter(
                xarr, yarr, symbol=symbol, size=size, name=name, **_face, **_edge
            )
        if len(yarrs) == 1:
            fig.axes.y.label = name
        return WidgetDataModel(value=fig, type=StandardType.PLOT, title="Plot")

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
        edge={"widget_type": EdgePropertyEdit, "value": _EDGE_ONLY_VALUE},
    )
    def configure_plot(
        x: tuple[slice, slice] | None,
        y: tuple[slice, slice],
        edge: dict = {},
    ) -> WidgetDataModel:
        fig = hplt.figure()
        xarr, yarrs = _get_xy_data(win, x, y, fig.axes)
        for name_yarr, _edge in zip(yarrs, _iter_edge(edge)):
            name, yarr = name_yarr
            fig.axes.plot(xarr, yarr, name=name, **_edge)
        if len(yarrs) == 1:
            fig.axes.y.label = name
        return WidgetDataModel(value=fig, type=StandardType.PLOT, title="Plot")

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
        fig = hplt.figure()
        if bottom is not None:
            _, bottoms = _get_xy_data(win, x, bottom, fig.axes)
        else:
            bottoms = itertools.repeat(None)
        xarr, yarrs = _get_xy_data(win, x, y, fig.axes)
        for name_yarr, name_bottom, _face, _edge in zip(
            yarrs, bottoms, _iter_face(face), _iter_edge(edge, prefix="edge_")
        ):
            name, yarr = name_yarr
            fig.axes.bar(
                xarr, yarr, bottom=name_bottom[1], bar_width=bar_width, name=name,
                **_face, **_edge
            )  # fmt: skip
        return WidgetDataModel(value=fig, type=StandardType.PLOT, title="Plot")

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
        edge={"widget_type": EdgePropertyEdit, "value": _EDGE_ONLY_VALUE},
    )
    def configure_plot(
        x: tuple[slice, slice] | None,
        y: tuple[slice, slice],
        xerr: tuple[slice, slice] | None,
        yerr: tuple[slice, slice] | None,
        capsize: float = 0.0,
        edge: dict = {},
    ) -> WidgetDataModel:
        fig = hplt.figure()
        if xerr is not None:
            _, xerrs = _get_xy_data(win, x, xerr, fig.axes)
        else:
            xerrs = itertools.repeat(None)
        if yerr is not None:
            _, yerrs = _get_xy_data(win, x, yerr, fig.axes)
        else:
            yerrs = itertools.repeat(None)
        xarr, yarrs = _get_xy_data(win, x, y, fig.axes)
        for name_yarr, _xerr, _yerr, _edge in zip(
            yarrs, xerrs, yerrs, _iter_edge(edge)
        ):
            name, yarr = name_yarr
            fig.axes.errorbar(
                xarr, yarr, x_error=_xerr, y_error=_yerr, capsize=capsize, name=name,
                **_edge,
            )  # fmt: skip
        return WidgetDataModel(value=fig, type=StandardType.PLOT, title="Plot")

    return configure_plot


@register_function(
    title="Band plot ...",
    types=_TABLE_LIKE,
    menus=_MENU,
    command_id="builtins:band-plot",
)
def band_plot(win: SubWindow) -> Parametric:
    @configure_gui(
        x={"widget_type": SelectionEdit, "getter": lambda: _range_getter(win)},
        y1={"widget_type": SelectionEdit, "getter": lambda: _range_getter(win)},
        y2={"widget_type": SelectionEdit, "getter": lambda: _range_getter(win)},
        face={"widget_type": FacePropertyEdit},
        edge={"widget_type": EdgePropertyEdit},
    )
    def configure_plot(
        x: tuple[slice, slice] | None,
        y1: tuple[slice, slice],
        y2: tuple[slice, slice],
        face: dict = {},
        edge: dict = {},
    ) -> WidgetDataModel:
        fig = hplt.figure()
        xarr, ydata1 = _get_xy_data(win, x, y1, fig.axes)
        _, ydata2 = _get_xy_data(win, x, y2, fig.axes)
        _face = next(_iter_face(face), {})
        _edge = next(_iter_edge(edge, prefix="edge_"), {})
        if len(ydata1) == 1 and len(ydata2) == 1:
            name, yar1 = ydata1[0]
            _, yar2 = ydata2[0]
            fig.axes.band(xarr, yar1, yar2, name=name, **_face, **_edge)
        else:
            raise ValueError("Only one pair of y values is allowed.")
        fig.axes.y.label = name
        return WidgetDataModel(value=fig, type=StandardType.PLOT, title="Plot")

    return configure_plot


@register_function(
    title="Edit plot ...",
    types=[StandardType.PLOT],
    menus="tools/plot",
    command_id="builtins:edit-plot",
)
def edit_plot(win: SubWindow) -> Parametric:
    model = win.to_model()
    if not isinstance(lo := model.value, hplt.BaseLayoutModel):
        raise ValueError("Invalid layout model")
    if isinstance(lo, hplt.SingleAxes):
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
    if not isinstance(meta := model.metadata, TableMeta):
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
    axes: hplt.Axes,
) -> "tuple[np.ndarray, list[tuple[str | None, np.ndarray]]]":
    from himena._data_wrappers import wrap_dataframe

    if y is None:
        raise ValueError("The y value must be given.")
    model = win.to_model()
    if is_subtype(model.type, StandardType.TABLE):
        xlabel, xarr, ys = _table_to_xy_data(model.value, x, y)
    elif is_subtype(model.type, StandardType.DATAFRAME):
        df = wrap_dataframe(model.value)
        column_names = df.column_names()[y[1].start, y[1].stop]
        rows = slice(y[0].start, y[0].stop)
        ys = [(cname, df.column_to_array(cname)[rows]) for cname in column_names]
        if x is None:
            xarr = np.arange(ys[0][1].size)
            xlabel = None
        else:
            column_names_x = df.column_names()[x[1].start, x[1].stop]
            if len(column_names_x) != 1:
                raise ValueError("x must not be more than one column.")
            xarr = df.column_to_array(column_names_x[0])
            xlabel = column_names_x[0]
    elif is_subtype(model.type, StandardType.EXCEL):
        if not isinstance(meta := model.metadata, ExcelMeta):
            raise ValueError("Must be a ExcelMeta")
        table = model.value[meta.current_sheet]
        xlabel, xarr, ys = _table_to_xy_data(table, x, y)
    else:
        raise RuntimeError(f"Unreachable: {model.type}")
    if xlabel:
        axes.x.label = xlabel
    return xarr, ys


def _table_to_xy_data(
    value: "np.ndarray",
    x: tuple[slice, slice] | None,
    y: tuple[slice, slice],
) -> "tuple[str | None, np.ndarray, list[tuple[str | None, np.ndarray]]]":
    parser = TableValueParser.from_array(value[y])
    if x is None:
        xarr = np.arange(parser.n_samples, dtype=np.float64)
        xlabel = None
    else:
        xlabel, xarr = parser.norm_x_value(value[x])
    return xlabel, xarr, parser._label_and_values


class TableValueParser:
    def __init__(
        self,
        label_and_values: "list[tuple[str | None, NDArray[np.float64]]]",
        is_column_vector: bool = True,
    ):
        self._label_and_values = label_and_values
        self._is_column_vector = is_column_vector

    @classmethod
    def from_columns(cls, value: "np.ndarray") -> "TableValueParser":
        nr, nc = value.shape
        if nr == 1:
            return cls([(None, value[:, i].astype(np.float64)) for i in range(nc)])
        try:
            value[0, :].astype(np.float64)  # try to cast to float
        except ValueError:
            # The first row is not numerical. Use it as labels.
            return cls(
                [(str(value[0, i]), value[1:, i].astype(np.float64)) for i in range(nc)]
            )
        else:
            return cls([(None, value[:, i].astype(np.float64)) for i in range(nc)])

    @classmethod
    def from_rows(cls, value: "np.ndarray") -> "TableValueParser":
        self = cls.from_columns(value.T)
        self._is_column_vector = False
        return self

    @classmethod
    def from_array(cls, value: "np.ndarray") -> "TableValueParser":
        try:
            return cls.from_columns(value)
        except ValueError:
            return cls.from_rows(value)

    @property
    def n_components(self) -> int:
        return len(self._label_and_values)

    @property
    def n_samples(self) -> int:
        return self._label_and_values[0][1].size

    def norm_x_value(self, arr: "np.ndarray") -> "tuple[str, NDArray[np.float64]]":
        # check if the first value is a label
        if self._is_column_vector and arr.shape[1] != 1:
            raise ValueError("The X values must be a 1D column vector.")
        if not self._is_column_vector and arr.shape[0] != 1:
            raise ValueError("The X values must be a 1D row vector.")
        arr = arr.ravel()
        try:
            arr[:1].astype(np.float64)
        except ValueError:
            label, arr_number = str(arr[0]), arr[1:].astype(np.float64)
        else:
            label, arr_number = None, arr.astype(np.float64)
        if arr_number.size != self.n_samples:
            raise ValueError("The number of X values must be the same as the Y values.")
        return label, arr_number


def _iter_face(face: "FacePropertyDict | dict", prefix: str = "") -> Iterator[dict]:
    color = face.get("color", None)
    hatch = face.get("hatch", None)
    if isinstance(color, Colormap):
        cycler = itertools.cycle(color.color_stops.colors)
    else:
        cycler = itertools.repeat(Color(color))
    while True:
        yield {f"{prefix}color": next(cycler), f"{prefix}hatch": hatch}


def _iter_edge(edge: "EdgePropertyDict | dict", prefix: str = "") -> Iterator[dict]:
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
