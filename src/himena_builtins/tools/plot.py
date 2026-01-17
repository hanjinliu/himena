from abc import ABC, abstractmethod
from typing import Any, Iterator, TypeVar
import warnings
from app_model import Action
from himena.plugins.actions import AppActionRegistry
from himena.utils import plot_functions
from himena.plugins import register_function, configure_gui, configure_submenu
from himena.types import Parametric, WidgetDataModel

from himena.consts import StandardType, MenuId
from himena.utils.misc import is_subtype
from himena.widgets import SubWindow

from himena.standards import plotting as hplt
from himena.standards.model_meta import DictMeta, TableMeta
from himena.qt.magicgui import AxisPropertyEdit, DictEdit
from himena._app_model import AppContext as _ctx

_MENU = [MenuId.TOOLS_PLOT, "/model_menu/plot"]
_NOT_AN_IMAGE = _ctx.active_window_model_subtype_1 != "image"

# Single 2D selection in the form of ((row start, row stop), (col start, col stop))
# We should avoid using slice because it is not serializable.
SelectionType = tuple[tuple[int, int], tuple[int, int]]

configure_submenu(MenuId.TOOLS_PLOT, group="20_builtins", order=32)


class PlotFactory(ABC):
    """Abstract base class for the built-in plot functions."""

    def __init__(self, subwindow: SubWindow):
        self._subwindow = subwindow

    def __init_subclass__(cls):
        reg = AppActionRegistry.instance()
        new_menus = [f"/model_menu:{tp}/plot" for tp in cls.model_types()]

        for action_kind in ["scatter", "line", "bar", "errorbar", "band", "histogram",
                            "scatter-plot-3d", "line-plot-3d"]:  # fmt: skip
            command_id = f"builtins:plot:{action_kind}"
            new_id = f"builtins:plot-factory-register-{cls.__name__}:{action_kind}"
            if action_orig := reg._actions.get(command_id):
                params = action_orig.model_dump()
                params["id"] = new_id
                params["menus"] = new_menus
                reg.add_action(Action(**params))
            else:  # pragma: no cover
                warnings.warn(
                    f"Original action {command_id} not found. This is an internal error.",
                    UserWarning,
                )

    def to_model(self) -> WidgetDataModel:
        """Return the WidgetDataModel from the subwindow.

        This is not necessarily the table widget."""
        return self._subwindow.to_model()

    @property
    def subwindow(self) -> SubWindow:
        """Return the subwindow associated with this factory."""
        return self._subwindow

    @classmethod
    @abstractmethod
    def model_types(cls) -> list[str]:
        """Return the supported model types for this plot factory."""

    @abstractmethod
    def table_data_model(self, **kwargs) -> WidgetDataModel:
        """Return the table type WidgetDataModel from this window for plotting."""

    @abstractmethod
    def prep_kwargs(self) -> dict[str, Any]:
        """Prepare keyword arguments for `table_data_model` method."""


_C = TypeVar("_C", bound=type)


def _iter_subclasses(cls: _C) -> Iterator[_C]:
    for subclass in cls.__subclasses__():
        yield subclass
        yield from _iter_subclasses(subclass)


def _pick_plot_factory(type: str) -> type[PlotFactory]:
    supported = [c for c in _iter_subclasses(PlotFactory) if c is not PlotFactory]
    for subclass in supported:
        for supported_type in subclass.model_types():
            if is_subtype(type, supported_type):
                return subclass
    types = sum([c.model_types() for c in supported], [])
    raise NotImplementedError(
        f"This plotting action is not implemented for data type {type!r}. Supported "
        f"types are: {types}"
    )


@register_function(
    title="Scatter Plot ...",
    menus=_MENU,
    command_id="builtins:plot:scatter",
    enablement=_NOT_AN_IMAGE,
)
def scatter_plot(win: SubWindow) -> Parametric:
    """Make a scatter plot from a table-like data."""
    factory = _pick_plot_factory(win.model_type())(win)
    return plot_functions.scatter(factory.table_data_model, factory.prep_kwargs)


@register_function(
    title="Line Plot ...",
    menus=_MENU,
    command_id="builtins:plot:line",
    enablement=_NOT_AN_IMAGE,
)
def line_plot(win: SubWindow) -> Parametric:
    """Make a line plot from a table-like data."""
    factory = _pick_plot_factory(win.model_type())(win)
    return plot_functions.line(factory.table_data_model, factory.prep_kwargs)


@register_function(
    title="Bar Plot ...",
    menus=_MENU,
    command_id="builtins:plot:bar",
    enablement=_NOT_AN_IMAGE,
)
def bar_plot(win: SubWindow) -> Parametric:
    """Make a bar plot from a table-like data."""
    factory = _pick_plot_factory(win.model_type())(win)
    return plot_functions.bar(factory.table_data_model, factory.prep_kwargs)


@register_function(
    title="Errorbar Plot ...",
    menus=_MENU,
    command_id="builtins:plot:errorbar",
    enablement=_NOT_AN_IMAGE,
)
def errorbar_plot(win: SubWindow) -> Parametric:
    """Make an error bar plot from a table-like data."""
    factory = _pick_plot_factory(win.model_type())(win)
    return plot_functions.errorbar(factory.table_data_model, factory.prep_kwargs)


@register_function(
    title="Band Plot ...",
    menus=_MENU,
    command_id="builtins:plot:band",
    enablement=_NOT_AN_IMAGE,
)
def band_plot(win: SubWindow) -> Parametric:
    """Make a band plot from a table-like data."""
    factory = _pick_plot_factory(win.model_type())(win)
    return plot_functions.band(factory.table_data_model, factory.prep_kwargs)


@register_function(
    title="Histogram Plot ...",
    menus=_MENU,
    command_id="builtins:plot:histogram",
    enablement=_NOT_AN_IMAGE,
)
def histogram(win: SubWindow) -> Parametric:
    """Make a histogram from a table-like data."""
    factory = _pick_plot_factory(win.model_type())(win)
    return plot_functions.histogram(factory.table_data_model, factory.prep_kwargs)


@register_function(
    title="3D Scatter Plot ...",
    menus=_MENU,
    command_id="builtins:plot:scatter-plot-3d",
    group="plot-3d",
    enablement=_NOT_AN_IMAGE,
)
def scatter_plot_3d(win: SubWindow) -> Parametric:
    """3D scatter plot."""
    factory = _pick_plot_factory(win.model_type())(win)
    return plot_functions.scatter_3d(factory.table_data_model, factory.prep_kwargs)


@register_function(
    title="3D Line Plot ...",
    menus=_MENU,
    command_id="builtins:plot:line-plot-3d",
    group="plot-3d",
    enablement=_NOT_AN_IMAGE,
)
def line_plot_3d(win: SubWindow) -> Parametric:
    """3D line plot."""
    factory = _pick_plot_factory(win.model_type())(win)
    return plot_functions.line_3d(factory.table_data_model, factory.prep_kwargs)


@register_function(
    title="Edit Plot ...",
    types=[StandardType.PLOT],
    menus=[MenuId.TOOLS_PLOT],
    command_id="builtins:plot:edit",
    keybindings="E",
)
def edit_plot(model: WidgetDataModel) -> Parametric:
    """Edit the appearance of the plot."""
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
    ) -> WidgetDataModel:
        lo.axes.title = title
        lo.axes.x = hplt.Axis.model_validate(x)
        lo.axes.y = hplt.Axis.model_validate(y)
        new_models = []
        for plot_model, value in zip(plot_models, kwargs.values()):
            dumped = plot_model.model_dump()
            dumped.update(value)
            new_models.append(plot_model.model_validate(dumped))
        lo.axes.models = new_models
        model.update_inplace = True
        return model

    return run_edit_plot


@register_function(
    title="Plot to DataFrame ...",
    types=StandardType.PLOT,
    menus=[MenuId.TOOLS_PLOT],
    command_id="builtins:plot:plot-to-dataframe",
)
def plot_to_dataframe(model: WidgetDataModel) -> Parametric:
    """Convert a plot component to a DataFrame."""

    lo = _get_single_axes(model)
    plot_models = lo.axes.models

    @configure_gui(component={"choices": _make_choices(plot_models)})
    def run(component: int) -> WidgetDataModel:
        """Convert the selected plot component to a DataFrame."""
        plot_model = plot_models[component]
        if isinstance(plot_model, hplt.Histogram):
            df = {
                "height": plot_model.height,
                "bin_start": plot_model.bins[:-1],
                "bin_end": plot_model.bins[1:],
            }
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


@register_function(
    title="Select Plot Components ...",
    types=StandardType.PLOT,
    menus=[MenuId.TOOLS_PLOT],
    command_id="builtins:plot:select-plot-components",
)
def select_plot_components(model: WidgetDataModel) -> Parametric:
    """Select a subset of the plot component."""
    lo = _get_single_axes(model)
    plot_models = lo.axes.models

    @configure_gui(
        components={"choices": _make_choices(plot_models), "widget_type": "Select"}
    )
    def run(components: list[int]) -> WidgetDataModel:
        models = [plot_models[i] for i in components]
        axes = lo.axes.model_copy(update={"models": models})
        out = lo.model_copy(update={"axes": axes})
        return model.with_value(out).with_title_numbering()

    return run


@register_function(
    title="Concatenate With ...",
    types=StandardType.PLOT,
    menus=[MenuId.TOOLS_PLOT],
    command_id="builtins:plot:concatenate-with",
)
def concatenate_with(model: WidgetDataModel) -> Parametric:
    """Concatenate the plot with another plot."""
    lo = _get_single_axes(model)

    @configure_gui(others={"types": StandardType.PLOT})
    def run(others: list[WidgetDataModel]) -> WidgetDataModel:
        """Concatenate the plot with another plot."""
        out = lo
        for other in others:
            lo_other = _get_single_axes(other)
            out = out.merge_with(lo_other)
        return model.with_value(out).with_title_numbering()

    return run


class DefaultPlotFactory(PlotFactory):
    @classmethod
    def model_types(cls) -> list[str]:
        return [StandardType.TABLE, StandardType.ARRAY, StandardType.DATAFRAME]

    def table_data_model(self) -> WidgetDataModel:
        return self.to_model()

    def prep_kwargs(self) -> dict[str, Any]:
        return {}


class ExcelPlotFactory(PlotFactory):
    @classmethod
    def model_types(cls) -> list[str]:
        return [StandardType.EXCEL]

    def table_data_model(self, current_tab: str) -> WidgetDataModel:
        model = self.to_model()
        meta = model.metadata
        if isinstance(meta, DictMeta):
            meta = meta.child_meta[current_tab]
        else:
            meta = TableMeta()
        data = model.value[current_tab]
        return WidgetDataModel(
            value=data,
            type=StandardType.TABLE,
            title=f"{model.title} - {current_tab}",
            metadata=meta,
        )

    def prep_kwargs(self) -> dict[str, Any]:
        model = self.to_model()
        if not isinstance(meta := model.metadata, DictMeta):
            raise ValueError("Metadata is not DictMeta for Excel data.")
        name = meta.current_tab
        if name is None:
            keys = list(meta.child_meta.keys())
            if not keys:
                raise ValueError("Data is empty.")
            name = keys[0]
        return {"current_tab": name}


def _get_single_axes(model: WidgetDataModel) -> hplt.SingleAxes | hplt.SingleAxes3D:
    if not isinstance(lo := model.value, hplt.BaseLayoutModel):
        raise ValueError(f"Expected a layout model, got {type(lo)}")
    if not isinstance(lo, (hplt.SingleAxes, hplt.SingleAxes3D)):
        raise NotImplementedError("Only SingleAxes is supported for now.")
    return lo


def _make_choices(models: list[hplt.BasePlotModel]) -> list[tuple[str, int]]:
    return [(f"({i}) {m.name}", i) for i, m in enumerate(models)]
