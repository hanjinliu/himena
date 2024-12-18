from __future__ import annotations

from typing import Callable, overload, TypeVar, TYPE_CHECKING
from cmap import Color
from himena.standards import plotting as hplt

if TYPE_CHECKING:
    from matplotlib import pyplot as plt
    from mpl_toolkits import mplot3d as plt3d

_CONVERSION_RULES: dict[
    type[hplt.BasePlotModel], Callable[[hplt.BasePlotModel, plt.Axes], None]
] = {}

_F = TypeVar("_F", bound=Callable)


@overload
def register_plot_model(
    model_class: type[hplt.BasePlotModel],
    rule: _F,
) -> _F: ...
@overload
def register_plot_model(
    model_class: type[hplt.BasePlotModel],
    rule: None,
) -> Callable[[_F], _F]: ...


def register_plot_model(
    model_class: type[hplt.BasePlotModel],
    rule: Callable[[hplt.BasePlotModel, plt.Axes], None] | None = None,
):
    """Register a matplotlib-specific conversion rule for a plot model."""

    def inner(f):
        _CONVERSION_RULES[model_class] = f
        return f

    return inner if rule is None else inner(rule)


def convert_plot_model(model: hplt.BasePlotModel, ax: plt.Axes):
    if model.__class__ in _CONVERSION_RULES:
        return _CONVERSION_RULES[model.__class__](model, ax)
    raise ValueError(f"Unsupported plot model: {model!r}")


@register_plot_model(hplt.Scatter)
def _(model: hplt.Scatter, ax: plt.Axes):
    if model.size is not None:
        s = model.size**2
    else:
        s = None
    ax.scatter(
        model.x, model.y, s=s, c=Color(model.face.color).hex,
        marker=model.symbol, linewidths=model.edge.width, hatch=model.face.hatch,
        edgecolors=model.edge.color, linestyle=model.edge.style or "-",
        label=model.name,
    )  # fmt: skip


@register_plot_model(hplt.Line)
def _(model: hplt.Line, ax: plt.Axes):
    ax.plot(
        model.x, model.y, color=model.edge.color, linewidth=model.edge.width,
        linestyle=model.edge.style, label=model.name,
    )  # fmt: skip


@register_plot_model(hplt.Bar)
def _(model: hplt.Bar, ax: plt.Axes):
    ax.bar(
        model.x, model.y, color=model.face.color, hatch=model.face.hatch,
        bottom=model.bottom, width=model.bar_width, edgecolor=model.edge.color,
        label=model.name, linewidth=model.edge.width, linestyle=model.edge.style,
    )  # fmt: skip


@register_plot_model(hplt.Histogram)
def _(model: hplt.Histogram, ax: plt.Axes):
    ax.hist(
        model.data, bins=model.bins, range=model.range, color=model.face.color,
        hatch=model.face.hatch, orientation=model.orient, edgecolor=model.edge.color,
        linewidth=model.edge.width, linestyle=model.edge.style, label=model.name,
    )  # fmt: skip


@register_plot_model(hplt.ErrorBar)
def _(model: hplt.ErrorBar, ax: plt.Axes):
    ax.errorbar(
        model.x, model.y, xerr=model.x_error, yerr=model.y_error,
        capsize=model.capsize, color=model.edge.color, linewidth=model.edge.width,
        linestyle=model.edge.style, label=model.name,
    )  # fmt: skip


@register_plot_model(hplt.Band)
def _(model: hplt.Band, ax: plt.Axes):
    ax.fill_between(
        model.x, model.y0, model.y1, color=model.face.color, hatch=model.face.hatch,
        edgecolor=model.edge.color, linewidth=model.edge.width,
        linestyle=model.edge.style, label=model.name,
    )  # fmt: skip


@register_plot_model(hplt.Scatter3D)
def _(model: hplt.Scatter3D, ax: plt3d.Axes3D):
    if model.size is not None:
        s = model.size**2
    else:
        s = 20
    ax.scatter(
        model.x, model.y, model.z, s=s, c=Color(model.face.color).hex,
        marker=model.symbol, linewidths=model.edge.width, hatch=model.face.hatch,
        edgecolors=model.edge.color, linestyle=model.edge.style or "-",
        label=model.name,
    )  # fmt: skip


@register_plot_model(hplt.Line3D)
def _(model: hplt.Line3D, ax: plt3d.Axes3D):
    ax.plot(
        model.x, model.y, model.z, color=model.edge.color, linewidth=model.edge.width,
        linestyle=model.edge.style, label=model.name,
    )  # fmt: skip


@register_plot_model(hplt.Mesh3D)
def _(model: hplt.Mesh3D, ax: plt3d.Axes3D):
    ax.plot_trisurf(
        model.vertices[:, 0], model.vertices[:, 1], model.vertices[:, 2],
        triangles=model.face_indices, color=model.face.color, edgecolor=model.edge.color,
        linewidth=model.edge.width, linestyle=model.edge.style, label=model.name,
    )  # fmt: skip
