from functools import partial
import inspect
from pathlib import Path
import html
import re
from typing import Any, Iterable, Literal, Mapping
import warnings
from datetime import datetime
import numpy as np
from himena.data_wrappers._dataframe import wrap_dataframe
from himena._descriptors import NoNeedToSave
from himena.exceptions import Cancelled
from himena.plugins import register_function, configure_gui, widget_classes
from himena.standards.model_meta import ListMeta
from himena.types import Parametric, WidgetDataModel
from himena.consts import StandardType, MonospaceFontFamily, MenuId
from himena.utils.collections import OrderedSet
from himena.widgets import SubWindow, MainWindow, ParametricWindow
from himena.workflow import Workflow, as_function, as_function_from_path
from himena import AppContext as ctx
from himena._utils import get_display_name, get_widget_class_id, unwrap_lazy_model


@register_function(
    types=StandardType.READER_NOT_FOUND,
    menus=[],
    command_id="builtins:open-as-text-anyway",
)
def open_as_text_anyway(ui: MainWindow, win: SubWindow) -> WidgetDataModel[str]:
    """Open as a text file."""
    model = win.to_model()
    if model.type != StandardType.READER_NOT_FOUND:
        raise ValueError(f"Invalid model type: {model.type}")
    if not isinstance(src := model.source, Path):
        raise ValueError(
            f"Model has multiple or no local source paths: {src}. Cannot open as a text data."
        )
    out = model.with_value(
        src.read_text(),
        type=StandardType.TEXT,
        save_behavior_override=NoNeedToSave(),
    )
    out.extension_default = src.suffix
    win._close_me(ui)
    return out


@register_function(
    menus=[MenuId.TOOLS_OTHERS],
    title="Stack models ...",
    command_id="builtins:models:stack-models",
    enablement=(ctx.num_tabs > 0) & (ctx.num_sub_windows > 0),
)
def stack_models(ui: MainWindow) -> Parametric:
    """Stack windows into a single window that contains a list of the models."""

    def run_stack_models(
        models: list[WidgetDataModel],
        pattern: str = "",
    ) -> WidgetDataModel:
        """Stack windows into a single window that contains a list of the models.

        Parameters
        ----------
        models : list of WidgetDataModel
            Models to stack.
        pattern : str
            A regular expression pattern to match the title of the models.
        """
        if models and pattern:
            raise ValueError("Cannot specify both models and patterns.")
        if not models and not pattern:
            raise ValueError("Must specify either models or patterns.")
        if pattern:
            pat = re.compile(pattern)
            models: list[WidgetDataModel] = []
            for win in ui.tabs.current():
                if isinstance(win, ParametricWindow):
                    continue
                model = win.to_model()
                if pat.match(model.title):
                    models.append(model)
            if not models:
                raise ValueError("No models matched the pattern.")
        return WidgetDataModel(
            value=models,
            type=StandardType.MODELS,
            title="Merged",
        )

    return run_stack_models


@register_function(
    menus=[MenuId.TOOLS_OTHERS],
    types=[StandardType.MODELS],
    command_id="builtins:models:sort-model-list",
)
def sort_model_list(model: WidgetDataModel) -> Parametric:
    """Sort the model list."""

    def run_sort(
        descending: bool = False,
        sort_by: Literal["title", "type", "time"] = "title",
    ) -> WidgetDataModel:
        """Run sorting.

        Parameters
        ----------
        descending : bool
            Sort by descending order.
        sort_by : str
            Specify how to sort the list.
        """
        if sort_by == "title":
            _sort_func = _sort_func_title
        elif sort_by == "type":
            _sort_func = _sort_func_type
        elif sort_by == "time":
            _sort_func = _sort_func_datetime
        else:
            raise ValueError(f"Invalid `sort_by` argument: {sort_by}")
        models = sorted(
            _norm_model_list(model.value), key=_sort_func, reverse=descending
        )
        return model.with_value(models, title=f"{model.title} sorted")

    return run_sort


def _sort_func_title(m: WidgetDataModel) -> str:
    return m.title


def _sort_func_type(m: WidgetDataModel) -> str:
    return m.type


def _sort_func_datetime(m: WidgetDataModel) -> datetime:
    if last := m.workflow.last():
        return last.datetime
    return datetime(9999, 12, 31)


@register_function(
    menus=[MenuId.TOOLS_OTHERS],
    types=[StandardType.MODELS],
    command_id="builtins:models:filter-model-list",
)
def filter_model_list(model: WidgetDataModel) -> Parametric:
    """Filter the model list."""

    def run_filter(
        model_type: str = "",
        title_contains: str = "",
        unwrap_lazy_objects: bool = True,
    ) -> WidgetDataModel:
        """Filter the model list.

        Parameters
        ----------
        model_type : str
            If specified, only models of this type will be included.
        title_contains : str
            If specified, only models with titles containing this string will be
            included.
        unwrap_lazy_objects : bool
            If True, lazy-type models will be unwrapped before filtering. If you added
            a element from a local file, it is usually a lazy object.
        """
        models_out: list[WidgetDataModel] = []
        for m in _norm_model_list(model.value):
            if not isinstance(m, WidgetDataModel):
                warnings.warn(
                    f"Expected a sequence of WidgetDataModel but got {type(m)} as an "
                    "element. Skipping.",
                    RuntimeWarning,
                    stacklevel=2,
                )
                continue
            if unwrap_lazy_objects and m.type == StandardType.LAZY:
                m = unwrap_lazy_model(m)
            if model_type and not m.is_subtype_of(model_type):
                continue
            if title_contains and title_contains not in m.title:
                continue
            models_out.append(m)
        return model.with_value(models_out, title=f"{model.title} filtered")

    return run_filter


@register_function(
    title="Compute lazy items",
    types=[StandardType.MODELS],
    menus=[MenuId.TOOLS_OTHERS],
    command_id="builtins:models:compute-lazy-items",
)
def compute_lazy_items(model: WidgetDataModel) -> WidgetDataModel:
    """Compute all the lazy items in the model list."""

    def _unwrap_list(mlist: list[WidgetDataModel]):
        out: list[WidgetDataModel] = []
        for m in _norm_model_list(mlist):
            if m.type == StandardType.LAZY:
                out.append(unwrap_lazy_model(m))
            elif m.is_subtype_of(StandardType.MODELS):
                out.append(m.with_value(_unwrap_list(m.value)))
            else:
                out.append(m)
        return out

    model_out = _unwrap_list(model.value)
    return model.with_value(model_out, title=f"{model.title} computed")


def _norm_model_list(models) -> Iterable[WidgetDataModel]:
    if isinstance(models, Mapping):
        return models.values()
    else:
        return models


@register_function(
    title="Execute workflow",
    types=[StandardType.WORKFLOW],
    menus=[],
    command_id="builtins:exec-workflow",
    enablement=ctx.active_window_model_subtype_1 != "parametric",
)
def exec_workflow(model: WidgetDataModel) -> None:
    """Execute the workflow."""
    # NOTE: this function should not return the model and let the application process
    # it. The workflow of the output model should not be updated. Using workflow to
    # compute a new model is a special case in himena.
    _cast_workflow(model).compute(process_output=True)


@register_function(
    title="Execute workflow",
    types=[StandardType.WORKFLOW_PARAMETRIC],
    menus=[],
    command_id="builtins:exec-parametric-workflow",
)
def exec_parametric_workflow(model: WidgetDataModel, ui: MainWindow) -> Parametric:
    """Execute the workflow."""
    wf = _cast_workflow(model)
    return as_function(wf)(ui)


@register_function(
    title="Execute workflow file",
    menus=[""],
    command_id="builtins:exec-workflow-file",
)
def exec_workflow_file(ui: MainWindow) -> Parametric:
    """Execute a workflow from a workflow file."""
    if path := ui.exec_file_dialog(
        extension_default=".workflow.json",
        allowed_extensions=[".txt", ".json", ".workflow.json"],
        caption="Select a workflow file",
        group="workflows",
    ):
        return as_function_from_path(path)(ui)
    raise Cancelled


def _cast_workflow(model: WidgetDataModel) -> Workflow:
    """Cast the model to a Workflow object."""
    if not isinstance(model.value, Workflow):
        raise TypeError(f"Expected a Workflow object but got {type(model.value)}")
    return model.value


@register_function(
    types=[
        StandardType.TEXT,
        StandardType.TABLE,
        StandardType.DATAFRAME,
        StandardType.ARRAY,
        StandardType.EXCEL,
    ],
    menus=["tools"],
    command_id="builtins:general:show-statistics",
)
def show_statistics(model: WidgetDataModel) -> WidgetDataModel:
    """Show the statistics of the data."""
    value = model.value
    if model.is_subtype_of(StandardType.TEXT):
        value_str = str(value)
        nchars = len(value_str)
        nlines = len(value_str.splitlines())
        out = (
            f"<b>Number of characters:</b> {nchars}<br><b>Number of lines:</b> {nlines}"
        )
    elif model.is_subtype_of(StandardType.TABLE):
        out = _statistics_table(value)
    elif model.is_subtype_of(StandardType.DATAFRAME):
        df = wrap_dataframe(value)
        nr, nc = df.shape
        columns = df.column_names()
        shape = f"<b>Shape:</b> {nr} rows, {nc} columns"
        dtypes = "".join(
            ["<li>"]
            + [f"<ul>{c!r}: {d.name}</ul>" for c, d in zip(columns, df.dtypes)]
            + ["</li>"]
        )
        stats = []
        for c in columns:
            ar = df.column_to_array(c)
            if ar.dtype.kind in "iuf":
                stats.append(
                    f"<b>{c!r}</b>: min={ar.min()}, max={ar.max()}, mean={ar.mean()}, std={ar.std(ddof=1)}"
                )
            elif ar.dtype.kind == "b":
                ntrue = ar.sum()
                stats.append(f"<b>{c!r}</b>: True ... {ntrue}/{len(ar)}")
        stats = "<br>" + "<br>".join(stats)
        out = shape + dtypes + stats
    elif model.is_subtype_of(StandardType.ARRAY):
        if not isinstance(value, np.ndarray):
            raise ValueError(f"Expected a numpy array but got {type(value)}")
        if value.dtype.names:
            out = f"<b>Shape:</b> {value.shape}"
        else:
            out = f"<b>Shape:</b> {value.shape}<br><b>Min:</b> {value.min()}<br><b>Max:</b> {value.max()}<br><b>Mean:</b> {value.mean()}<br><b>Std:</b> {value.std(ddof=1)}"
    elif model.is_subtype_of(StandardType.EXCEL):
        value = model.value
        if not isinstance(value, dict):
            raise ValueError(f"Expected a dict but got {type(out)}")
        out = []
        for key, val in value.items():
            out.append(f"<h3><u>{key}</u></h3>{_statistics_table(val)}")
        out = "".join(out)
    else:
        raise NotImplementedError(f"Statistics for {model.type} is not implemented.")
    return WidgetDataModel(
        value=out,
        type=StandardType.HTML,
        title=f"Statistics of {model.title}",
        extension_default=".html",
        editable=False,
        save_behavior_override=NoNeedToSave(),
    )


@register_function(
    menus=["tools"],
    command_id="builtins:general:show-metadata",
)
def show_metadata(model: WidgetDataModel) -> WidgetDataModel:
    """Show the metadata of the underlying data."""
    meta = model.metadata
    if meta is None:
        out = "<No metadata>"
    elif hasattr(meta, "_repr_html_"):
        out = meta._repr_html_()
    else:
        meta_repr = html.escape(repr(meta))
        out = (
            f"<span style='font-family: monaco,{MonospaceFontFamily},"
            f"monospace;'>{meta_repr}</span>"
        )
    return WidgetDataModel(
        value=out,
        type=StandardType.HTML,
        title=f"Metadata of {model.title}",
        editable=False,
        save_behavior_override=NoNeedToSave(),
    )


@register_function(
    title="Specify widget ...",
    menus=["tools"],
    command_id="builtins:specify-widget",
)
def specify_widget(model: WidgetDataModel) -> Parametric:
    """Manually specify the type of the data.

    This function will force the data to be open with the specified widget. Whether the
    widget supports the value will not be checked.
    """
    classes = sorted(widget_classes().items(), key=lambda x: x[0])
    choices = [
        (f"{get_display_name(c, sep=' ')}", c)
        for t, c in classes
        if t != StandardType.READER_NOT_FOUND
    ]

    @configure_gui(widget_class={"choices": choices}, show_parameter_labels=False)
    def run_specify(widget_class: type) -> WidgetDataModel:
        return model.with_open_plugin(
            open_with=get_widget_class_id(widget_class),
            save_behavior_override=NoNeedToSave(),
        )

    return run_specify


@register_function(
    title="Partialize function ...",
    menus=[MenuId.TOOLS_FUNCTION],
    types=[StandardType.FUNCTION],
    command_id="builtins:partialize-function",
)
def partialize_function(model: WidgetDataModel) -> Parametric:
    """Partialize the function."""
    import ast

    if not callable(func := model.value):
        raise ValueError(f"Expected a callable object but got {type(func)}")

    options = {}
    sig = inspect.signature(func)
    for name, param in sig.parameters.items():
        if param.default is param.empty:
            options[name] = {"label": name, "widget_type": "LineEdit", "value": ""}
        else:
            options[name] = {
                "label": name,
                "widget_type": "LineEdit",
                "value": str(param.default),
            }

    @configure_gui(gui_options=options)
    def run_partialize(**kwargs: str) -> WidgetDataModel:
        kwargs_evaled = {k: ast.literal_eval(v) for k, v in kwargs.items() if v.strip()}
        return WidgetDataModel(
            value=partial(func, **kwargs_evaled),
            type=StandardType.FUNCTION,
            title=f"[Partial] {model.title}",
        )

    return run_partialize


@register_function(
    title="Plot y = f(x)...",
    menus=[MenuId.TOOLS_FUNCTION],
    types=[StandardType.FUNCTION],
    command_id="builtins:plot-function-1d",
)
def plot_function_1d(model: WidgetDataModel) -> Parametric:
    """Plot function by its first argument."""

    def run_plot(
        xmin: float = -1, xmax: float = 1, num_points: int = 100
    ) -> WidgetDataModel:
        func = model.value
        x = np.linspace(xmin, xmax, num_points)
        y = func(x)
        return WidgetDataModel(
            value={"x": x, "y": y},
            type=StandardType.DATAFRAME_PLOT,
            title=f"Plot of {model.title}",
        )

    return run_plot


@register_function(
    title="Plot z = f(x, y)...",
    menus=[MenuId.TOOLS_FUNCTION],
    types=[StandardType.FUNCTION],
    command_id="builtins:plot-function-2d",
)
def plot_function_2d(model: WidgetDataModel) -> Parametric:
    """Plot function by its first two arguments."""
    from himena.standards import plotting as hplt

    def run_plot(
        xmin: float = -1,
        xmax: float = 1,
        ymin: float = -1,
        ymax: float = 1,
        num_points: int = 100,
    ) -> WidgetDataModel:
        func = model.value
        xvals = np.linspace(xmin, xmax, num_points)
        yvals = np.linspace(ymin, ymax, num_points)
        x, y = np.meshgrid(xvals, yvals)
        z = func(x, y)
        fig = hplt.figure_3d()
        fig.axes.surface(x, y, z)
        return WidgetDataModel(
            value=fig,
            type=StandardType.PLOT,
            title=f"Plot of {model.title}",
        )

    return run_plot


@register_function(
    title="Results To Table",
    menus=[MenuId.TOOLS_OTHERS],
    types=[StandardType.RESULTS],
    command_id="builtins:results:results-to-table",
)
def results_to_table(model: WidgetDataModel) -> WidgetDataModel:
    """Convert the result stack to a table."""
    vals: list[dict[str, Any]] = model.value
    return _results_to_table(vals, title=f"{model.title} (Table)")


@register_function(
    title="Results To Table (Selected)",
    menus=[MenuId.TOOLS_OTHERS],
    types=[StandardType.RESULTS],
    command_id="builtins:results:selected-results-to-table",
)
def selected_results_to_table(model: WidgetDataModel) -> WidgetDataModel:
    """Convert the selected results to a table."""
    meta = model.metadata
    if not isinstance(meta, ListMeta):
        raise ValueError(f"Expected a ListMeta but got {type(meta)}")
    vals: list[dict[str, Any]] = [model.value[i] for i in meta.selections]
    if not vals:
        raise ValueError("No item selected.")
    return _results_to_table(vals, title=f"{model.title} (Table)")


def _results_to_table(vals: list[dict[str, Any]], title: str) -> WidgetDataModel:
    """Convert the result stack to a table."""
    columns = OrderedSet[str]()
    for val in vals:
        if not isinstance(val, dict):
            raise TypeError(f"Expected a dict but got {type(val)}")
        columns.update(val.keys())
    column_name_to_index = {name: i for i, name in enumerate(columns)}
    arr = np.zeros((len(vals) + 1, len(columns)), dtype=np.dtypes.StringDType())
    arr[0, :] = [str(name) for name in columns]
    for i, val in enumerate(vals):
        for name, value in val.items():
            if name not in column_name_to_index:
                raise ValueError(f"Unknown column name: {name}")
            arr[i + 1, column_name_to_index[name]] = str(value)
    return WidgetDataModel(
        value=arr,
        type=StandardType.TABLE,
        title=title,
    )


def _statistics_table(value) -> str:
    if value is None:
        value = np.array([[""]], dtype=np.dtypes.StringDType())
    if not isinstance(value, np.ndarray):
        raise ValueError(
            f"Expected a numpy array for the table data but got {type(value)}"
        )
    if not isinstance(value.dtype, np.dtypes.StringDType):
        raise ValueError(f"Expected a numpy array of strings but got {value.dtype}")
    nrows, ncols = value.shape
    n_empty = int((value == "").ravel().sum())
    nchars = len(value.ravel().sum())
    out = (
        f"<b>Number of rows:</b> {nrows}<br>"
        f"<b>Number of columns:</b> {ncols}<br>"
        f"<b>Number of empty cells:</b> {n_empty}<br>"
        f"<b>Number of non-empty cells:</b> {nrows * ncols - n_empty}<br>"
        f"<b>Number of characters:</b> {nchars}"
    )
    return out
