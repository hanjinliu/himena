from typing import TYPE_CHECKING, Iterator
import itertools

from cmap import Color, Colormap
import numpy as np

from himena._utils import to_color_or_colormap
from himena.plugins import register_function, configure_gui
from himena.types import Parametric, WidgetDataModel
from himena.utils.table_selection import (
    model_to_xy_arrays,
    table_selection_gui_option,
    auto_select,
)
from himena.consts import StandardType, MenuId
from himena.widgets import SubWindow
from himena.standards import plotting as hplt
from himena.qt.magicgui import (
    FacePropertyEdit,
    EdgePropertyEdit,
    AxisPropertyEdit,
    DictEdit,
)

if TYPE_CHECKING:
    from himena.qt.magicgui._plot_elements import FacePropertyDict, EdgePropertyDict

_TABLE_LIKE = [
    StandardType.TABLE,
    StandardType.ARRAY,
    StandardType.DATAFRAME,
    StandardType.EXCEL,
]
_MENU = [MenuId.TOOLS_PLOT, "/model_menu/plot"]
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
def scatter_plot(win: SubWindow) -> Parametric:
    """Make a scatter plot."""
    x0, y0 = auto_select(win.to_model(), 2)

    @configure_gui(
        x=table_selection_gui_option(win, default=x0),
        y=table_selection_gui_option(win, default=y0),
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
        model = win.to_model()
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
def line_plot(win: SubWindow) -> Parametric:
    x0, y0 = auto_select(win.to_model(), 2)

    @configure_gui(
        x=table_selection_gui_option(win, default=x0),
        y=table_selection_gui_option(win, default=y0),
        edge={"widget_type": EdgePropertyEdit, "value": _EDGE_ONLY_VALUE},
    )
    def configure_plot(
        x: SelectionType | None,
        y: SelectionType,
        edge: dict = {},
    ) -> WidgetDataModel:
        model = win.to_model()
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
def bar_plot(win: SubWindow) -> Parametric:
    model = win.to_model()
    x0, y0 = auto_select(model, 2)

    @configure_gui(
        x=table_selection_gui_option(win, default=x0),
        y=table_selection_gui_option(win, default=y0),
        bottom=table_selection_gui_option(win),
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
        model = win.to_model()
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
def errorbar_plot(win: SubWindow) -> Parametric:
    x0, y0 = auto_select(win.to_model(), 2)

    @configure_gui(
        x=table_selection_gui_option(win, default=x0),
        y=table_selection_gui_option(win, default=y0),
        xerr=table_selection_gui_option(win),
        yerr=table_selection_gui_option(win),
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
        model = win.to_model()
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
def band_plot(win: SubWindow) -> Parametric:
    x0, y10, y20 = auto_select(win.to_model(), 3)

    @configure_gui(
        x=table_selection_gui_option(win, default=x0),
        y0=table_selection_gui_option(win, default=y10),
        y1=table_selection_gui_option(win, default=y20),
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
        model = win.to_model()
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
def histogram(win: SubWindow) -> Parametric:
    x0 = auto_select(win.to_model(), 1)[0]
    assert x0 is not None  # when num == 1, it must be a tuple.
    row_sel = x0[0]
    ndata = row_sel[1] - row_sel[0]

    @configure_gui(
        x=table_selection_gui_option(win, default=x0),
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
        model = win.to_model()
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
    menus=[MenuId.TOOLS_PLOT],
    command_id="builtins:edit-plot",
)
def edit_plot(win: SubWindow) -> Parametric:
    """Edit the appearance of the plot."""
    model = win.to_model()
    lo = _get_single_axes(model)
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
    command_id="builtins:plot-3d:scatter-plot-3d",
)
def scatter_plot_3d(win: SubWindow) -> Parametric:
    """3D scatter plot."""
    x0, y0, z0 = auto_select(win.to_model(), 3)

    @configure_gui(
        x=table_selection_gui_option(win, default=x0),
        y=table_selection_gui_option(win, default=y0),
        z=table_selection_gui_option(win, default=z0),
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
        model = win.to_model()
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
    command_id="builtins:plot-3d:line-plot-3d",
)
def line_plot_3d(win: SubWindow) -> Parametric:
    """3D line plot."""
    x0, y0, z0 = auto_select(win.to_model(), 3)

    @configure_gui(
        x=table_selection_gui_option(win, default=x0),
        y=table_selection_gui_option(win, default=y0),
        z=table_selection_gui_option(win, default=z0),
        edge={"widget_type": EdgePropertyEdit, "value": _EDGE_ONLY_VALUE},
    )
    def configure_plot(
        x: SelectionType,
        y: SelectionType,
        z: SelectionType,
        edge: dict = {},
    ) -> WidgetDataModel:
        model = win.to_model()
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


@register_function(
    title="Plot to DataFrame ...",
    types=StandardType.PLOT,
    menus=[MenuId.TOOLS_PLOT],
    command_id="builtins:plot-to-dataframe",
)
def plot_to_dataframe(model: WidgetDataModel) -> Parametric:
    """Convert a plot component to a DataFrame."""

    lo = _get_single_axes(model)
    plot_models = lo.axes.models
    choices = [(f"({i}) {m.name}", i) for i, m in enumerate(plot_models)]

    @configure_gui(component={"choices": choices})
    def run(component: int) -> WidgetDataModel:
        """Convert the selected plot component to a DataFrame."""
        plot_model = plot_models[component]
        if isinstance(plot_model, hplt.Histogram):
            df = {"data": plot_model.data}
        elif isinstance(plot_model, hplt.Texts):
            df = {"x": plot_model.x, "y": plot_model.y, "text": plot_model.texts}
        elif isinstance(plot_model, hplt.ErrorBar):
            df = {
                "x": plot_model.x,
                "y": plot_model.y,
                "x_error": plot_model.x_error,
                "y_error": plot_model.y_error,
            }
        elif isinstance(plot_model, hplt.Span):
            df = {"start": plot_model.start, "end": plot_model.end}
        elif isinstance(plot_model, hplt.models.PlotModelXY):
            df = {"x": plot_model.x, "y": plot_model.y}
        elif isinstance(plot_model, hplt.Band):
            df = {"x": plot_model.x, "y0": plot_model.y0, "y1": plot_model.y1}
        elif isinstance(plot_model, (hplt.Scatter3D, hplt.Line3D)):
            df = {"x": plot_model.x, "y": plot_model.y, "z": plot_model.z}
        else:
            raise NotImplementedError(f"Type {type(plot_model)} is not supported.")
        return WidgetDataModel(
            value=df,
            type=StandardType.DATAFRAME,
            title=f"Data of {model.title}",
        )

    return run


def _get_xy_data(
    model: WidgetDataModel,
    x: SelectionType | None,
    y: SelectionType | None,
    axes: hplt.Axes,
) -> "tuple[np.ndarray, list[tuple[str | None, np.ndarray]]]":
    xarr, yarrs = model_to_xy_arrays(model, x, y)
    if xarr.name:
        axes.x.label = xarr.name
    return xarr.array, yarrs


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


def _get_single_axes(model: WidgetDataModel) -> hplt.SingleAxes | hplt.SingleAxes3D:
    if not isinstance(lo := model.value, hplt.BaseLayoutModel):
        raise ValueError(f"Expected a layout model, got {type(lo)}")
    if not isinstance(lo, (hplt.SingleAxes, hplt.SingleAxes3D)):
        raise NotImplementedError("Only SingleAxes is supported for now.")
    return lo
