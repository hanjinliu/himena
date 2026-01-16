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


def scatter(factory: Callable[[], WidgetDataModel]) -> Parametric:
    """Plugin function for creating a scatter plot from table data factory."""
    x0, y0 = auto_select(factory(), 2)

    @configure_gui(
        x=table_selection_gui_option(factory, default=x0),
        y=table_selection_gui_option(factory, default=y0),
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
        model = factory()
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
