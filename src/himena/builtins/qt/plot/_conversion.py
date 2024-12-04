from __future__ import annotations

from typing import Callable, overload, TypeVar, TYPE_CHECKING
from cmap import Color
from himena.standards import plotting as hplt

if TYPE_CHECKING:
    from matplotlib import pyplot as plt

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


def _convert_plot_model(model: hplt.BasePlotModel, ax: plt.Axes):
    if model.__class__ in _CONVERSION_RULES:
        return _CONVERSION_RULES[model.__class__](model, ax)
    raise ValueError(f"Unsupported plot model: {model}")


@register_plot_model(hplt.Scatter)
def _(model: hplt.Scatter, ax: plt.Axes):
    ax.scatter(
        model.x, model.y, s=model.size ** 2, c=Color(model.face.color).hex,
        marker=model.symbol, linewidths=model.edge.width, hatch=model.face.hatch,
        edgecolors=model.edge.color, linestyle=model.edge.style, label=model.name,
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


def _convert_axes(ax: hplt.Axes, ax_mpl: plt.Axes):
    if ax.title is not None:
        title, style = _parse_styled_text(ax.title)
        ax_mpl.set_title(title, **style)
    if ax.x is not None:
        if ax.x.label is not None:
            xlabel, style = _parse_styled_text(ax.x.label)
            ax_mpl.set_xlabel(xlabel, **style)
        if ax.x.ticks is not None:
            ax_mpl.set_xticks(ax.x.ticks)
        if ax.x.lim is not None:
            ax_mpl.set_xlim(ax.x.lim)
        if ax.x.scale == "log":
            ax_mpl.set_xscale("log")
    if ax.y is not None:
        if ax.y.label is not None:
            ylabel, style = _parse_styled_text(ax.y.label)
            ax_mpl.set_ylabel(ylabel, **style)
        if ax.y.ticks is not None:
            ax_mpl.set_yticks(ax.y.ticks)
        if ax.y.lim is not None:
            ax_mpl.set_ylim(ax.y.lim)
        if ax.y.scale == "log":
            ax_mpl.set_yscale("log")
    for model in ax.models:
        _convert_plot_model(model, ax_mpl)


def convert_plot_layout(lo: hplt.BaseLayoutModel, fig: plt.Figure):
    if isinstance(lo, hplt.SingleAxes):
        if len(fig.axes) != 1:
            fig.clear()
            axes = fig.add_subplot(111)
        else:
            axes = fig.axes[0]
        axes.clear()
        _convert_axes(lo.axes, axes)
    elif isinstance(lo, hplt.Layout1D):
        _shape = (1, len(lo.axes)) if isinstance(lo, hplt.Row) else (len(lo.axes), 1)
        if len(fig.axes) != len(lo.axes):
            fig.clear()
            axes = fig.subplots(*_shape, sharex=lo.share_x, sharey=lo.share_y)
        else:
            axes = fig.axes
        for ax, ax_mpl in zip(lo.axes, axes):
            _convert_axes(ax, ax_mpl)
    elif isinstance(lo, hplt.Grid):
        raise NotImplementedError("Grid layout is not supported yet")
    else:
        raise ValueError(f"Unsupported layout model: {lo}")


def _parse_styled_text(text: hplt.StyledText | str) -> tuple[str, dict]:
    if isinstance(text, str):
        return text, {}
    fontdict = {}
    if text.size is not None:
        fontdict["size"] = text.size
    if text.family:
        fontdict["family"] = text.family
    if text.bold:
        fontdict["weight"] = "bold"
    if text.italic:
        fontdict["style"] = "italic"
    if text.underline:
        fontdict["decoration"] = "underline"
    if text.color:
        fontdict["color"] = text.color
    loc = text.alignment
    return text.text, {"fontdict": fontdict, "loc": loc}
