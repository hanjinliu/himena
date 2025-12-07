from __future__ import annotations

from typing import TYPE_CHECKING, Any
from himena.standards import plotting as hplt
from himena_builtins.qt.plot._register import convert_plot_model

if TYPE_CHECKING:
    from matplotlib import pyplot as plt
    from mpl_toolkits import mplot3d as plt3d


def _refer_x_axis(ax: hplt.Axis, ax_mpl: plt.Axes):
    if ax.label is not None:
        ax_mpl.set_xlabel(ax.label)
    if ax.ticks is not None:
        ax_mpl.set_xticks(ax.ticks.pos, ax.ticks.labels)
    if ax.lim is not None:
        ax_mpl.set_xlim(ax.lim)
    if ax.scale == "log":
        ax_mpl.set_xscale("log")


def _refer_y_axis(ax: hplt.Axis, ax_mpl: plt.Axes):
    if ax.label is not None:
        ax_mpl.set_ylabel(ax.label)
    if ax.ticks is not None:
        ax_mpl.set_yticks(ax.ticks.pos, ax.ticks.labels)
    if ax.lim is not None:
        ax_mpl.set_ylim(ax.lim)
    if ax.scale == "log":
        ax_mpl.set_yscale("log")


def _refer_z_axis(ax: hplt.Axis, ax_mpl: plt3d.Axes3D):
    if ax.label is not None:
        ax_mpl.set_zlabel(ax.label)
    if ax.ticks is not None:
        ax_mpl.set_zticks(ax.ticks.pos, ax.ticks.labels)
    if ax.lim is not None:
        ax_mpl.set_zlim(ax.lim)
    if ax.scale == "log":
        ax_mpl.set_zscale("log")


def _refer_title(ax: hplt.Axes, ax_mpl: plt.Axes):
    title, style = _parse_styled_text(ax.title)
    ax_mpl.set_title(title, **style)


def update_mpl_axes_by_model(ax: hplt.Axes, ax_mpl: plt.Axes):
    ax_mpl.spines["left"].set_edgecolor(ax.axis_color)
    ax_mpl.spines["bottom"].set_edgecolor(ax.axis_color)
    if ax.title is not None:
        _refer_title(ax, ax_mpl)
    if ax.x is not None:
        _refer_x_axis(ax.x, ax_mpl)
    if ax.y is not None:
        _refer_y_axis(ax.y, ax_mpl)
    for model in ax.models:
        convert_plot_model(model, ax_mpl)
    if legend := ax.legend:
        loc, bbox_to_anchor = _LEGEND_LOC_MAP[legend.location]
        leg = ax_mpl.legend(
            loc=loc, bbox_to_anchor=bbox_to_anchor, prop={"size": legend.font_size}
        )
        if isinstance(legend.title, hplt.StyledText):
            title, style = _parse_styled_text(legend.title)
            leg.set_title(title, **style)
        elif isinstance(legend.title, str):
            leg.set_title(legend.title)


def _convert_axes_3d(ax: hplt.Axes3D, ax_mpl: plt3d.Axes3D):
    if ax.title is not None:
        _refer_title(ax, ax_mpl)
    if ax.x is not None:
        _refer_x_axis(ax.x, ax_mpl)
    if ax.y is not None:
        _refer_y_axis(ax.y, ax_mpl)
    if ax.z is not None:
        _refer_z_axis(ax.z, ax_mpl)
    for model in ax.models:
        convert_plot_model(model, ax_mpl)


def _fill_axis_props(axes: hplt.Axes, axes_mpl: plt.Axes):
    """Fill Nones in model axis from the matplotlib axis."""
    axes = axes.model_copy()
    if axes.title is None:
        axes.title = axes_mpl.get_title()
    if axes.x.lim is None:
        axes.x.lim = axes_mpl.get_xlim()
    if axes.x.label is None:
        axes.x.label = axes_mpl.get_xlabel()
    if axes.y.lim is None:
        axes.y.lim = axes_mpl.get_ylim()
    if axes.y.label is None:
        axes.y.label = axes_mpl.get_ylabel()
    return axes


def update_model_axis_by_mpl(axes: hplt.Axes, axes_mpl: plt.Axes):
    """Update model axis from the matplotlib axis."""
    axes.title = axes_mpl.get_title()
    axes.x.lim = axes_mpl.get_xlim()
    axes.x.label = axes_mpl.get_xlabel()
    axes.y.lim = axes_mpl.get_ylim()
    axes.y.label = axes_mpl.get_ylabel()
    return axes


def convert_plot_layout(lo: hplt.BaseLayoutModel, fig: plt.Figure):
    fig.patch.set_facecolor(lo.background_color)
    if isinstance(lo, hplt.SingleAxes):
        ax_mpl = _get_single_mpl_axes(fig)
        update_mpl_axes_by_model(lo.axes, ax_mpl)
        ax_mpl.patch.set_color(lo.background_color)
        lo.axes = _fill_axis_props(lo.axes, ax_mpl)
    elif isinstance(lo, hplt.layout.Layout1D):
        _shape = (1, len(lo.axes)) if isinstance(lo, hplt.Row) else (len(lo.axes), 1)
        if len(fig.axes) != len(lo.axes):
            fig.clear()
            axes = fig.subplots(*_shape, sharex=lo.share_x, sharey=lo.share_y)
        else:
            axes = fig.axes
        for ax, ax_mpl in zip(lo.axes, axes):
            update_mpl_axes_by_model(ax, ax_mpl)
            ax_mpl.patch.set_color(lo.background_color)
        lo.axes = [_fill_axis_props(ax, ax_mpl) for ax, ax_mpl in zip(lo.axes, axes)]
    elif isinstance(lo, hplt.Grid):
        raise NotImplementedError("Grid layout is not supported yet")
    elif isinstance(lo, hplt.SingleAxes3D):
        ax_mpl = _get_single_mpl_axes(fig, projection="3d")
        _convert_axes_3d(lo.axes, ax_mpl)
        ax_mpl.patch.set_color(lo.background_color)
        lo.axes = _fill_axis_props(lo.axes, ax_mpl)
    elif isinstance(lo, hplt.SingleStackedAxes):
        ax_mpl = _get_single_mpl_axes(fig)
        ax_mpl.patch.set_color(lo.background_color)
    else:
        raise ValueError(f"Unsupported layout model: {lo}")
    return lo


def _get_single_mpl_axes(fig: plt.Figure, **kwargs) -> plt.Axes:
    if len(fig.axes) != 1:
        fig.clear()
        ax_mpl = fig.add_subplot(111, **kwargs)
    else:
        ax_mpl = fig.axes[0]
        ax_mpl.clear()
    return ax_mpl


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


_LEGEND_LOC_MAP: dict[hplt.LegendLocation, tuple[str, Any]] = {
    hplt.LegendLocation.TOP_RIGHT: ("upper right", None),
    hplt.LegendLocation.TOP_CENTER: ("upper center", None),
    hplt.LegendLocation.TOP_LEFT: ("upper left", None),
    hplt.LegendLocation.BOTTOM_RIGHT: ("lower right", None),
    hplt.LegendLocation.BOTTOM_CENTER: ("lower center", None),
    hplt.LegendLocation.BOTTOM_LEFT: ("lower left", None),
    hplt.LegendLocation.CENTER_RIGHT: ("center right", None),
    hplt.LegendLocation.CENTER_LEFT: ("center left", None),
    hplt.LegendLocation.CENTER: ("center", None),
    hplt.LegendLocation.TOP_SIDE_LEFT: ("lower left", (0, 1.02)),
    hplt.LegendLocation.TOP_SIDE_CENTER: ("lower center", (0.5, 1.02)),
    hplt.LegendLocation.TOP_SIDE_RIGHT: ("lower right", (1, 1.02)),
    hplt.LegendLocation.BOTTOM_SIDE_LEFT: ("upper left", (0, -0.02)),
    hplt.LegendLocation.BOTTOM_SIDE_CENTER: ("upper center", (0.5, -0.02)),
    hplt.LegendLocation.BOTTOM_SIDE_RIGHT: ("upper right", (1, -0.02)),
    hplt.LegendLocation.LEFT_SIDE_TOP: ("upper right", (-0.02, 1)),
    hplt.LegendLocation.LEFT_SIDE_CENTER: ("center right", (-0.02, 0.5)),
    hplt.LegendLocation.LEFT_SIDE_BOTTOM: ("lower right", (-0.02, 0)),
    hplt.LegendLocation.RIGHT_SIDE_TOP: ("upper left", (1.02, 1)),
    hplt.LegendLocation.RIGHT_SIDE_CENTER: ("center left", (1.02, 0.5)),
    hplt.LegendLocation.RIGHT_SIDE_BOTTOM: ("lower left", (1.02, 0)),
}
