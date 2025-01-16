from typing import TYPE_CHECKING, Callable, Iterator
import itertools

from cmap import Color, Colormap
import numpy as np

from himena._utils import to_color_or_colormap
from himena.plugins import register_function, configure_gui
from himena.types import Parametric, WidgetDataModel, is_subtype
from himena.consts import StandardType
from himena.widgets import SubWindow
from himena.standards.model_meta import ExcelMeta, TableMeta
from himena.standards import plotting as hplt
from himena.qt._magicgui import (
    SelectionEdit,
    FacePropertyEdit,
    EdgePropertyEdit,
    AxisPropertyEdit,
    DictEdit,
)

if TYPE_CHECKING:
    from numpy.typing import NDArray
    from himena.qt._magicgui._plot_elements import FacePropertyDict, EdgePropertyDict

_TABLE_LIKE = [StandardType.TABLE, StandardType.DATAFRAME, StandardType.EXCEL]
_MENU = ["tools/plot", "/model_menu/plot"]
_EDGE_ONLY_VALUE = {"color": "tab10", "width": 2.0}

# Single 2D selection in the form of ((row start, row stop), (col start, col stop))
# We should avoid using slice because it is not serializable.
SelectionType = tuple[tuple[int, int], tuple[int, int]]


@register_function(
    title="Scatter plot ...",
    types=_TABLE_LIKE,
    menus=_MENU,
    command_id="builtins:scatter-plot",
)
def scatter_plot(model: WidgetDataModel) -> Parametric:
    x0, y0 = _auto_select(model, 2)

    @configure_gui(
        x={"widget_type": SelectionEdit, "getter": _range_getter(model), "value": x0},
        y={"widget_type": SelectionEdit, "getter": _range_getter(model), "value": y0},
        face={"widget_type": FacePropertyEdit},
        edge={"widget_type": EdgePropertyEdit},
    )
    def configure_plot(
        x: SelectionType | None,
        y: SelectionType,
        symbol: str = "o",
        size: float = 6.0,
        face: dict = {},
        edge: dict = {},
    ) -> WidgetDataModel:
        fig = hplt.figure()
        xarr, yarrs = _get_xy_data(model, x, y, fig.axes)
        for name_yarr, _face, _edge in zip(
            yarrs, _iter_face(face), _iter_edge(edge, prefix="edge_")
        ):
            name, yarr = name_yarr
            fig.axes.scatter(
                xarr, yarr, symbol=symbol, size=size, name=name, **_face, **_edge
            )
        if len(yarrs) == 1:
            fig.axes.y.label = name
        return WidgetDataModel(
            value=fig,
            type=StandardType.PLOT,
            title=f"Plot of {model.title}",
        )

    return configure_plot


@register_function(
    title="Line plot ...",
    types=_TABLE_LIKE,
    menus=_MENU,
    command_id="builtins:line-plot",
)
def line_plot(model: WidgetDataModel) -> Parametric:
    x0, y0 = _auto_select(model, 2)

    @configure_gui(
        x={"widget_type": SelectionEdit, "getter": _range_getter(model), "value": x0},
        y={"widget_type": SelectionEdit, "getter": _range_getter(model), "value": y0},
        edge={"widget_type": EdgePropertyEdit, "value": _EDGE_ONLY_VALUE},
    )
    def configure_plot(
        x: SelectionType | None,
        y: SelectionType,
        edge: dict = {},
    ) -> WidgetDataModel:
        fig = hplt.figure()
        xarr, yarrs = _get_xy_data(model, x, y, fig.axes)
        for name_yarr, _edge in zip(yarrs, _iter_edge(edge)):
            name, yarr = name_yarr
            fig.axes.plot(xarr, yarr, name=name, **_edge)
        if len(yarrs) == 1:
            fig.axes.y.label = name
        return WidgetDataModel(
            value=fig,
            type=StandardType.PLOT,
            title=f"Plot of {model.title}",
        )

    return configure_plot


@register_function(
    title="Bar plot ...",
    types=_TABLE_LIKE,
    menus=_MENU,
    command_id="builtins:bar-plot",
)
def bar_plot(model: WidgetDataModel) -> Parametric:
    x0, y0 = _auto_select(model, 2)

    @configure_gui(
        x={"widget_type": SelectionEdit, "getter": _range_getter(model), "value": x0},
        y={"widget_type": SelectionEdit, "getter": _range_getter(model), "value": y0},
        bottom={"widget_type": SelectionEdit, "getter": _range_getter(model)},
        face={"widget_type": FacePropertyEdit},
        edge={"widget_type": EdgePropertyEdit},
    )
    def configure_plot(
        x: SelectionType | None,
        y: SelectionType,
        bottom: SelectionType | None = None,
        bar_width: float = 0.8,
        face: dict = {},
        edge: dict = {},
    ) -> WidgetDataModel:
        fig = hplt.figure()
        if bottom is not None:
            _, bottoms = _get_xy_data(model, x, bottom, fig.axes)
        else:
            bottoms = itertools.repeat(None)
        xarr, yarrs = _get_xy_data(model, x, y, fig.axes)
        for name_yarr, name_bottom, _face, _edge in zip(
            yarrs, bottoms, _iter_face(face), _iter_edge(edge, prefix="edge_")
        ):
            name, yarr = name_yarr
            fig.axes.bar(
                xarr, yarr, bottom=_ignore_label(name_bottom), bar_width=bar_width,
                name=name, **_face, **_edge
            )  # fmt: skip
        return WidgetDataModel(
            value=fig,
            type=StandardType.PLOT,
            title=f"Plot of {model.title}",
        )

    return configure_plot


@register_function(
    title="Errorbar plot ...",
    types=_TABLE_LIKE,
    menus=_MENU,
    command_id="builtins:errorbar-plot",
)
def errorbar_plot(model: WidgetDataModel) -> Parametric:
    x0, y0 = _auto_select(model, 2)

    @configure_gui(
        x={"widget_type": SelectionEdit, "getter": _range_getter(model), "value": x0},
        y={"widget_type": SelectionEdit, "getter": _range_getter(model), "value": y0},
        xerr={"widget_type": SelectionEdit, "getter": _range_getter(model)},
        yerr={"widget_type": SelectionEdit, "getter": _range_getter(model)},
        edge={"widget_type": EdgePropertyEdit, "value": _EDGE_ONLY_VALUE},
    )
    def configure_plot(
        x: SelectionType | None,
        y: SelectionType,
        xerr: SelectionType | None,
        yerr: SelectionType | None,
        capsize: float = 0.0,
        edge: dict = {},
    ) -> WidgetDataModel:
        fig = hplt.figure()
        if xerr is not None:
            _, xerrs = _get_xy_data(model, x, xerr, fig.axes)
        else:
            xerrs = itertools.repeat(None)
        if yerr is not None:
            _, yerrs = _get_xy_data(model, x, yerr, fig.axes)
        else:
            yerrs = itertools.repeat(None)
        xarr, yarrs = _get_xy_data(model, x, y, fig.axes)
        for name_yarr, _xer, _yer, _edge in zip(yarrs, xerrs, yerrs, _iter_edge(edge)):
            name, yarr = name_yarr
            fig.axes.errorbar(
                xarr, yarr, x_error=_ignore_label(_xer), y_error=_ignore_label(_yer),
                capsize=capsize, name=name, **_edge,
            )  # fmt: skip
        return WidgetDataModel(
            value=fig,
            type=StandardType.PLOT,
            title=f"Plot of {model.title}",
        )

    return configure_plot


@register_function(
    title="Band plot ...",
    types=_TABLE_LIKE,
    menus=_MENU,
    command_id="builtins:band-plot",
)
def band_plot(model: WidgetDataModel) -> Parametric:
    x0, y10, y20 = _auto_select(model, 3)

    @configure_gui(
        x={"widget_type": SelectionEdit, "getter": _range_getter(model), "value": x0},
        y0={"widget_type": SelectionEdit, "getter": _range_getter(model), "value": y10},
        y1={"widget_type": SelectionEdit, "getter": _range_getter(model), "value": y20},
        face={"widget_type": FacePropertyEdit},
        edge={"widget_type": EdgePropertyEdit},
    )
    def configure_plot(
        x: SelectionType | None,
        y0: SelectionType,
        y1: SelectionType,
        face: dict = {},
        edge: dict = {},
    ) -> WidgetDataModel:
        fig = hplt.figure()
        xarr, ydata1 = _get_xy_data(model, x, y0, fig.axes)
        _, ydata2 = _get_xy_data(model, x, y1, fig.axes)
        _face = next(_iter_face(face), {})
        _edge = next(_iter_edge(edge, prefix="edge_"), {})
        if len(ydata1) == 1 and len(ydata2) == 1:
            name, yar1 = ydata1[0]
            _, yar2 = ydata2[0]
            fig.axes.band(xarr, yar1, yar2, name=name, **_face, **_edge)
        else:
            raise ValueError("Only one pair of y values is allowed.")
        fig.axes.y.label = name
        return WidgetDataModel(
            value=fig,
            type=StandardType.PLOT,
            title=f"Plot of {model.title}",
        )

    return configure_plot


@register_function(
    title="Histogram ...",
    types=_TABLE_LIKE,
    menus=_MENU,
    command_id="builtins:histogram",
)
def histogram(model: WidgetDataModel) -> Parametric:
    x0 = _auto_select(model, 1)[0]
    assert x0 is not None  # when num == 1, it must be a tuple.
    row_sel = x0[0]
    ndata = row_sel[1] - row_sel[0]

    @configure_gui(
        x={"widget_type": SelectionEdit, "getter": _range_getter(model), "value": x0},
        bins={"min": 1, "value": max(int(np.sqrt(ndata)), 2)},
        face={"widget_type": FacePropertyEdit},
        edge={"widget_type": EdgePropertyEdit},
    )
    def configure_plot(
        x: SelectionType | None,
        bins: int = 10,
        face: dict = {},
        edge: dict = {},
    ) -> WidgetDataModel:
        fig = hplt.figure()
        _, yarrs = _get_xy_data(model, None, x, fig.axes)
        for name_yarr, _face, _edge in zip(
            yarrs, _iter_face(face), _iter_edge(edge, prefix="edge_")
        ):
            name, yarr = name_yarr
            fig.axes.hist(yarr, bins=bins, name=name, **_face, **_edge)
        fig.axes.x.label = name
        return WidgetDataModel(
            value=fig,
            type=StandardType.PLOT,
            title=f"Plot of {model.title}",
        )

    return configure_plot


@register_function(
    title="Edit plot ...",
    types=[StandardType.PLOT],
    menus="tools/plot",
    command_id="builtins:edit-plot",
)
def edit_plot(win: SubWindow) -> Parametric:
    """Edit the appearance of the plot."""
    model = win.to_model()
    if not isinstance(lo := model.value, hplt.BaseLayoutModel):
        raise ValueError("Invalid layout model")
    if not isinstance(lo, hplt.SingleAxes):
        raise NotImplementedError("Only SingleAxes is supported for now.")
    plot_models = lo.axes.models
    gui_options = {
        "title": {"widget_type": "LineEdit", "value": lo.axes.title or ""},
        "x": {"widget_type": AxisPropertyEdit, "value": lo.axes.x.model_dump()},
        "y": {"widget_type": AxisPropertyEdit, "value": lo.axes.y.model_dump()},
    }
    for i, m in enumerate(plot_models):
        opt = {
            "label": f"#{i}",
            "widget_type": DictEdit,
            "options": m.plot_option_dict(),
            "value": m.model_dump(),
        }
        gui_options[f"element_{i}"] = opt

    @configure_gui(gui_options=gui_options)
    def run_edit_plot(
        title: str,
        x: dict,
        y: dict,
        **kwargs: dict,
    ):
        lo.axes.title = title
        lo.axes.x = hplt.Axis.model_validate(x)
        lo.axes.y = hplt.Axis.model_validate(y)
        new_models = []
        for plot_model, value in zip(plot_models, kwargs.values()):
            dumped = plot_model.model_dump()
            dumped.update(value)
            new_models.append(plot_model.model_validate(dumped))
        lo.axes.models = new_models
        win.update_model(model)
        return None

    return run_edit_plot


@register_function(
    title="Scatter plot 3D ...",
    types=_TABLE_LIKE,
    menus=_MENU,
    command_id="builtins:scatter-plot-3d",
)
def scatter_plot_3d(model: WidgetDataModel) -> Parametric:
    x0, y0, z0 = _auto_select(model, 3)

    @configure_gui(
        x={"widget_type": SelectionEdit, "getter": _range_getter(model), "value": x0},
        y={"widget_type": SelectionEdit, "getter": _range_getter(model), "value": y0},
        z={"widget_type": SelectionEdit, "getter": _range_getter(model), "value": z0},
        face={"widget_type": FacePropertyEdit},
        edge={"widget_type": EdgePropertyEdit},
    )
    def configure_plot(
        x: SelectionType,
        y: SelectionType,
        z: SelectionType,
        symbol: str = "o",
        size: float = 6.0,
        face: dict = {},
        edge: dict = {},
    ) -> WidgetDataModel:
        fig = hplt.figure_3d()
        xarr, yarrs = _get_xy_data(model, x, y, fig.axes)
        _, zarrs = _get_xy_data(model, x, z, fig.axes)

        if len(yarrs) == 1 and len(zarrs) == 1:
            name_y, yarr = yarrs[0]
            name_z, zarr = zarrs[0]
            _face = next(_iter_face(face), {})
            _edge = next(_iter_edge(edge, prefix="edge_"), {})
            fig.axes.scatter(
                xarr, yarr, zarr, symbol=symbol, size=size, name=name_z, **_face,
                **_edge
            )  # fmt: skip
        else:
            raise ValueError("Only one pair of y values is allowed.")
        fig.axes.y.label = name_y
        fig.axes.z.label = name_z
        return WidgetDataModel(
            value=fig,
            type=StandardType.PLOT,
            title=f"Plot of {model.title}",
        )

    return configure_plot


@register_function(
    title="Line plot 3D ...",
    types=_TABLE_LIKE,
    menus=_MENU,
    command_id="builtins:line-plot-3d",
)
def line_plot_3d(model: WidgetDataModel) -> Parametric:
    x0, y0, z0 = _auto_select(model, 3)

    @configure_gui(
        x={"widget_type": SelectionEdit, "getter": _range_getter(model), "value": x0},
        y={"widget_type": SelectionEdit, "getter": _range_getter(model), "value": y0},
        z={"widget_type": SelectionEdit, "getter": _range_getter(model), "value": z0},
        edge={"widget_type": EdgePropertyEdit, "value": _EDGE_ONLY_VALUE},
    )
    def configure_plot(
        x: SelectionType,
        y: SelectionType,
        z: SelectionType,
        edge: dict = {},
    ) -> WidgetDataModel:
        fig = hplt.figure_3d()
        xarr, yarrs = _get_xy_data(model, x, y, fig.axes)
        _, zarrs = _get_xy_data(model, x, z, fig.axes)
        if len(yarrs) == 1 and len(zarrs) == 1:
            name_y, yarr = yarrs[0]
            name_z, zarr = zarrs[0]
            _edge = next(_iter_edge(edge), {})
            fig.axes.plot(xarr, yarr, zarr, name=name_z, **_edge)
        else:
            raise ValueError("Only one pair of y values is allowed.")
        fig.axes.y.label = name_y
        fig.axes.z.label = name_z
        return WidgetDataModel(
            value=fig,
            type=StandardType.PLOT,
            title=f"Plot of {model.title}",
        )

    return configure_plot


def _range_getter(
    model: WidgetDataModel,
) -> Callable[[], tuple[SelectionType, SelectionType]]:
    """The getter function for SelectionEdit"""

    def _getter():
        types = [StandardType.TABLE, StandardType.DATAFRAME, StandardType.EXCEL]
        if model.type not in types:
            raise ValueError(f"Cannot plot model of type {model.type!r}")
        if not isinstance(meta := model.metadata, TableMeta):
            raise ValueError("Excel must have TableMeta as the additional data.")

        if len(meta.selections) == 0:
            raise ValueError(f"No selection found in window {model.title!r}")
        elif len(meta.selections) > 1:
            raise ValueError(f"More than one selection found in window {model.title!r}")
        sel = meta.selections[0]
        rindices, cindices = sel
        _assert_tuple_of_ints(rindices)
        _assert_tuple_of_ints(cindices)
        return rindices, cindices

    return _getter


def _assert_tuple_of_ints(value: tuple[int, int]) -> None:
    if not isinstance(value, tuple) or len(value) != 2:
        raise ValueError("Must be a tuple of two integers.")
    if not all(isinstance(v, int) for v in value):
        raise ValueError("Must be a tuple of two integers.")


def _get_xy_data(
    model: WidgetDataModel,
    x: SelectionType | None,
    y: SelectionType | None,
    axes: hplt.Axes,
) -> "tuple[np.ndarray, list[tuple[str | None, np.ndarray]]]":
    from himena._data_wrappers import wrap_dataframe

    if y is None:
        raise ValueError("The y value must be given.")
    if is_subtype(model.type, StandardType.TABLE):
        xlabel, xarr, ys = _table_to_xy_data(model.value, x, y)
    elif is_subtype(model.type, StandardType.DATAFRAME):
        df = wrap_dataframe(model.value)
        column_names = df.column_names()[y[1][0] : y[1][1]]
        rows = slice(y[0][0], y[0][1])
        ys = [(cname, df.column_to_array(cname)[rows]) for cname in column_names]
        if x is None:
            xarr = np.arange(ys[0][1].size)
            xlabel = None
        else:
            column_names_x = df.column_names()[x[1][0] : x[1][1]]
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
        raise ValueError(f"Table-like data expected, but got model type {model.type!r}")
    if xlabel:
        axes.x.label = xlabel
    return xarr, ys


def _auto_select(model: WidgetDataModel, num: int) -> "list[None | SelectionType]":
    from himena._data_wrappers import wrap_dataframe

    selections: list[tuple[tuple[int, int], tuple[int, int]]] = []
    model_type = model.type
    if is_subtype(model_type, StandardType.TABLE):
        val = model.value
        if not isinstance(val, np.ndarray):
            raise ValueError(f"Table must be a numpy array, got {type(val)}")
        shape = val.shape
        if isinstance(meta := model.metadata, TableMeta):
            selections = meta.selections
    elif is_subtype(model_type, StandardType.DATAFRAME):
        df = wrap_dataframe(model.value)
        shape = df.shape
        if isinstance(meta := model.metadata, TableMeta):
            selections = meta.selections
    elif is_subtype(model_type, StandardType.EXCEL):
        if not isinstance(meta := model.metadata, ExcelMeta):
            raise ValueError(f"Expected an ExcelMeta, got {type(meta)}")
        table = model.value[meta.current_sheet]
        if not isinstance(table, np.ndarray):
            raise ValueError(f"Table must be a numpy array, got {type(table)}")
        shape = table.shape
        selections = meta.selections
    else:
        raise ValueError(f"Table-like data expected, but got model type {model_type!r}")
    ncols = shape[1]
    if num == len(selections):
        return selections
    if ncols == 0:
        raise ValueError("The table must have at least one column.")
    elif ncols < num:
        out = [None] * num
        for i in range(ncols):
            out[i + num - ncols] = ((0, shape[0]), (i, i + 1))
        return out
    else:
        return [((0, shape[0]), (i, i + 1)) for i in range(num)]


def _table_to_xy_data(
    value: "np.ndarray",
    x: SelectionType | None,
    y: SelectionType,
) -> "tuple[str | None, np.ndarray, list[tuple[str | None, np.ndarray]]]":
    ysl = slice(y[0][0], y[0][1]), slice(y[1][0], y[1][1])
    parser = TableValueParser.from_array(value[ysl])
    if x is None:
        xarr = np.arange(parser.n_samples, dtype=np.float64)
        xlabel = None
    else:
        xsl = slice(x[0][0], x[0][1]), slice(x[1][0], x[1][1])
        xlabel, xarr = parser.norm_x_value(value[xsl])
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
    color = to_color_or_colormap(face.get("color", "gray"))
    hatch = face.get("hatch", None)
    if isinstance(color, Colormap):
        cycler = itertools.cycle(color.color_stops.colors)
    else:
        cycler = itertools.repeat(Color(color))
    while True:
        yield {f"{prefix}color": next(cycler), f"{prefix}hatch": hatch}


def _iter_edge(edge: "EdgePropertyDict | dict", prefix: str = "") -> Iterator[dict]:
    color = to_color_or_colormap(edge.get("color", "gray"))
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


def _ignore_label(
    named_array: tuple[str | None, np.ndarray] | None,
) -> np.ndarray | None:
    if named_array is not None:
        _, val = named_array
    else:
        val = None
    return val
