from cmap import Color
from matplotlib import pyplot as plt
from himena.plotting import models, layout


def _convert_plot_model(model: models.BasePlotModel, ax: plt.Axes):
    if isinstance(model, models.Scatter):
        ax.scatter(
            model.x, model.y, s=model.size ** 2, c=Color(model.color).hex,
            marker=model.symbol, linewidths=model.edge_width,
            edgecolors=model.edge_color, label=model.name,
        )  # fmt: skip
    elif isinstance(model, models.Line):
        ax.plot(
            model.x, model.y, color=model.color, linewidth=model.width,
            linestyle=model.style, label=model.name,
        )  # fmt: skip
    elif isinstance(model, models.Bar):
        ax.bar(
            model.x, model.y, color=model.color, hatch=model.hatch, bottom=model.bottom,
            width=model.bar_width, edgecolor=model.edge_color, label=model.name,
            linewidth=model.edge_width, linestyle=model.edge_style,
        )  # fmt: skip
    elif isinstance(model, models.Histogram):
        ax.hist(
            model.data, bins=model.bins, color=model.color, range=model.range,
            orientation=model.orient, hatch=model.hatch, edgecolor=model.edge_color,
            linewidth=model.edge_width, linestyle=model.edge_style, label=model.name,
        )  # fmt: skip
    elif isinstance(model, models.ErrorBar):
        ax.errorbar(
            model.x, model.y, xerr=model.x_error, yerr=model.y_error,
            capsize=model.capsize, color=model.color, linewidth=model.width,
            linestyle=model.style, label=model.name,
        )  # fmt: skip
    else:
        raise ValueError(f"Unsupported plot model: {model}")


def _convert_axes(ax: layout.Axes, ax_mpl: plt.Axes):
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


def convert_plot_layout(lo: layout.BaseLayoutModel, fig: plt.Figure):
    if isinstance(lo, layout.SingleAxes):
        if len(fig.axes) != 1:
            fig.clear()
            axes = fig.add_subplot(111)
        else:
            axes = fig.axes[0]
        axes.clear()
        _convert_axes(lo.axes, axes)
    elif isinstance(lo, layout.Layout1D):
        _shape = (1, len(lo.axes)) if isinstance(lo, layout.Row) else (len(lo.axes), 1)
        if len(fig.axes) != len(lo.axes):
            fig.clear()
            axes = fig.subplots(*_shape, sharex=lo.share_x, sharey=lo.share_y)
        else:
            axes = fig.axes
        for ax, ax_mpl in zip(lo.axes, axes):
            _convert_axes(ax, ax_mpl)
    elif isinstance(lo, layout.Grid):
        raise NotImplementedError("Grid layout is not supported yet")
    else:
        raise ValueError(f"Unsupported layout model: {lo}")


def _parse_styled_text(text: layout.StyledText | str) -> tuple[str, dict]:
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
