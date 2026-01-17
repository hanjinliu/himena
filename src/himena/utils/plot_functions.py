from typing import TYPE_CHECKING, Callable, Iterator
import itertools

from cmap import Color, Colormap
import numpy as np

from himena._utils import to_color_or_colormap
from himena.plugins import configure_gui
from himena.types import Parametric, WidgetDataModel
from himena.utils.table_selection import (
    model_to_xy_arrays,
    table_selection_gui_option,
    auto_select,
    get_table_shape_and_selections,
)
from himena.consts import StandardType
from himena.standards import plotting as hplt
from himena.qt.magicgui import (
    FacePropertyEdit,
    EdgePropertyEdit,
)

if TYPE_CHECKING:
    from himena.qt.magicgui._plot_elements import FacePropertyDict, EdgePropertyDict

SelectionType = tuple[tuple[int, int], tuple[int, int]]
_EDGE_ONLY_VALUE = {"color": "tab10", "width": 2.0}


def partial_factory(
    factory: Callable[..., WidgetDataModel], factory_kwargs: Callable[[], dict]
) -> Callable[[], WidgetDataModel]:
    """Create a partial factory function with fixed keyword arguments."""

    def inner() -> WidgetDataModel:
        return factory(**factory_kwargs())

    return inner


def scatter(
    factory: Callable[..., WidgetDataModel],
    factory_kwargs: Callable[[], dict] | None = None,
) -> Parametric:
    """Plugin function for creating a scatter plot from table data factory."""
    factory_kwargs = factory_kwargs or (lambda: {})
    factory_partial = partial_factory(factory, factory_kwargs)
    try:
        x0, y0 = auto_select(factory_partial(), 2)
    except Exception:
        x0, y0 = None, None

    @configure_gui(
        x=table_selection_gui_option(factory_partial, default=x0),
        y=table_selection_gui_option(factory_partial, default=y0),
        face={"widget_type": FacePropertyEdit},
        edge={"widget_type": EdgePropertyEdit},
        gui_options={"factory_kwargs": {"bind": lambda *_: factory_kwargs()}},
    )
    def configure_plot(
        x: SelectionType | None,
        y: SelectionType,
        symbol: str = "o",
        size: float = 6.0,
        face: dict = {},
        edge: dict = {},
        factory_kwargs: dict = {},
    ) -> WidgetDataModel:
        model = factory(**factory_kwargs)
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


def line(
    factory: Callable[..., WidgetDataModel],
    factory_kwargs: Callable[[], dict] | None = None,
) -> Parametric:
    factory_kwargs = factory_kwargs or (lambda: {})
    factory_partial = partial_factory(factory, factory_kwargs)
    try:
        x0, y0 = auto_select(factory_partial(), 2)
    except Exception:
        x0, y0 = None, None

    @configure_gui(
        x=table_selection_gui_option(factory_partial, default=x0),
        y=table_selection_gui_option(factory_partial, default=y0),
        edge={"widget_type": EdgePropertyEdit, "value": _EDGE_ONLY_VALUE},
        gui_options={"factory_kwargs": {"bind": lambda *_: factory_kwargs()}},
    )
    def configure_plot(
        x: SelectionType | None,
        y: SelectionType,
        edge: dict = {},
        factory_kwargs: dict = {},
    ) -> WidgetDataModel:
        model = factory(**factory_kwargs)
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


def bar(
    factory: Callable[..., WidgetDataModel],
    factory_kwargs: Callable[[], dict] | None = None,
) -> Parametric:
    factory_kwargs = factory_kwargs or (lambda: {})
    factory_partial = partial_factory(factory, factory_kwargs)
    try:
        x0, y0 = auto_select(factory_partial(), 2)
    except Exception:
        x0, y0 = None, None

    @configure_gui(
        x=table_selection_gui_option(factory_partial, default=x0),
        y=table_selection_gui_option(factory_partial, default=y0),
        bottom=table_selection_gui_option(factory_partial),
        face={"widget_type": FacePropertyEdit},
        edge={"widget_type": EdgePropertyEdit},
        gui_options={"factory_kwargs": {"bind": lambda *_: factory_kwargs()}},
    )
    def configure_plot(
        x: SelectionType | None,
        y: SelectionType,
        bottom: SelectionType | None = None,
        bar_width: float = 0.8,
        face: dict = {},
        edge: dict = {},
        factory_kwargs: dict = {},
    ) -> WidgetDataModel:
        model = factory(**factory_kwargs)
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


def errorbar(
    factory: Callable[..., WidgetDataModel],
    factory_kwargs: Callable[[], dict] | None = None,
) -> Parametric:
    factory_kwargs = factory_kwargs or (lambda: {})
    factory_partial = partial_factory(factory, factory_kwargs)
    try:
        x0, y0 = auto_select(factory_partial(), 2)
    except Exception:
        x0, y0 = None, None

    @configure_gui(
        x=table_selection_gui_option(factory_partial, default=x0),
        y=table_selection_gui_option(factory_partial, default=y0),
        xerr=table_selection_gui_option(factory_partial),
        yerr=table_selection_gui_option(factory_partial),
        edge={"widget_type": EdgePropertyEdit, "value": _EDGE_ONLY_VALUE},
        gui_options={"factory_kwargs": {"bind": lambda *_: factory_kwargs()}},
    )
    def configure_plot(
        x: SelectionType | None,
        y: SelectionType,
        xerr: SelectionType | None,
        yerr: SelectionType | None,
        capsize: float = 0.0,
        edge: dict = {},
        factory_kwargs: dict = {},
    ) -> WidgetDataModel:
        model = factory(**factory_kwargs)
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


def band(
    factory: Callable[..., WidgetDataModel],
    factory_kwargs: Callable[[], dict] | None = None,
) -> Parametric:
    factory_kwargs = factory_kwargs or (lambda: {})
    factory_partial = partial_factory(factory, factory_kwargs)
    try:
        x0, y10, y20 = auto_select(factory_partial(), 3)
    except Exception:
        x0, y10, y20 = None, None, None

    @configure_gui(
        x=table_selection_gui_option(factory_partial, default=x0),
        y0=table_selection_gui_option(factory_partial, default=y10),
        y1=table_selection_gui_option(factory_partial, default=y20),
        face={"widget_type": FacePropertyEdit},
        edge={"widget_type": EdgePropertyEdit},
        gui_options={"factory_kwargs": {"bind": lambda *_: factory_kwargs()}},
    )
    def configure_plot(
        x: SelectionType | None,
        y0: SelectionType,
        y1: SelectionType,
        face: dict = {},
        edge: dict = {},
        factory_kwargs: dict = {},
    ) -> WidgetDataModel:
        model = factory(**factory_kwargs)
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


def histogram(
    factory: Callable[..., WidgetDataModel],
    factory_kwargs: Callable[[], dict] | None = None,
) -> Parametric:
    factory_kwargs = factory_kwargs or (lambda: {})
    factory_partial = partial_factory(factory, factory_kwargs)
    try:
        model = factory_partial()
        shape, selections = get_table_shape_and_selections(model)
        x0 = auto_select(model, 1)[0]
        assert x0 is not None  # when num == 1, it must be a tuple.
    except Exception:
        x0 = None
        shape = (10, 1)

    @configure_gui(
        x=table_selection_gui_option(factory_partial, default=x0),
        bins={"min": 1, "value": max(int(np.sqrt(shape[0])), 2)},
        face={"widget_type": FacePropertyEdit},
        edge={"widget_type": EdgePropertyEdit},
        gui_options={"factory_kwargs": {"bind": lambda *_: factory_kwargs()}},
    )
    def configure_plot(
        x: SelectionType | None,
        bins: int = 10,
        face: dict = {},
        edge: dict = {},
        factory_kwargs: dict = {},
    ) -> WidgetDataModel:
        model = factory(**factory_kwargs)
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


def scatter_3d(
    factory: Callable[..., WidgetDataModel],
    factory_kwargs: Callable[[], dict] | None = None,
) -> Parametric:
    factory_kwargs = factory_kwargs or (lambda: {})
    factory_partial = partial_factory(factory, factory_kwargs)
    try:
        x0, y0, z0 = auto_select(factory_partial(), 3)
    except Exception:
        x0, y0, z0 = None, None, None

    @configure_gui(
        x=table_selection_gui_option(factory_partial, default=x0),
        y=table_selection_gui_option(factory_partial, default=y0),
        z=table_selection_gui_option(factory_partial, default=z0),
        face={"widget_type": FacePropertyEdit},
        edge={"widget_type": EdgePropertyEdit},
        gui_options={"factory_kwargs": {"bind": lambda *_: factory_kwargs()}},
    )
    def configure_plot(
        x: SelectionType,
        y: SelectionType,
        z: SelectionType,
        symbol: str = "o",
        size: float = 6.0,
        face: dict = {},
        edge: dict = {},
        factory_kwargs: dict = {},
    ) -> WidgetDataModel:
        model = factory(**factory_kwargs)
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


def line_3d(
    factory: Callable[..., WidgetDataModel],
    factory_kwargs: Callable[[], dict] | None = None,
) -> Parametric:
    factory_kwargs = factory_kwargs or (lambda: {})
    factory_partial = partial_factory(factory, factory_kwargs)
    try:
        x0, y0, z0 = auto_select(factory_partial(), 3)
    except Exception:
        x0, y0, z0 = None, None, None

    @configure_gui(
        x=table_selection_gui_option(factory_partial, default=x0),
        y=table_selection_gui_option(factory_partial, default=y0),
        z=table_selection_gui_option(factory_partial, default=z0),
        edge={"widget_type": EdgePropertyEdit, "value": _EDGE_ONLY_VALUE},
        gui_options={"factory_kwargs": {"bind": lambda *_: factory_kwargs()}},
    )
    def configure_plot(
        x: SelectionType,
        y: SelectionType,
        z: SelectionType,
        edge: dict = {},
        factory_kwargs: dict = {},
    ) -> WidgetDataModel:
        model = factory(**factory_kwargs)
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
