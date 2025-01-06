from functools import partial
import inspect
from pathlib import Path
import html
import re
from typing import Literal, Mapping
import warnings
from datetime import datetime
import numpy as np
from himena._data_wrappers._dataframe import wrap_dataframe
from himena._descriptors import NoNeedToSave
from himena.plugins import register_function, configure_gui, widget_classes
from himena.types import Parametric, WidgetDataModel, is_subtype
from himena.consts import StandardType, MonospaceFontFamily
from himena.widgets import SubWindow, MainWindow, ParametricWindow
from himena.workflow import Workflow
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
    if not isinstance(model.source, Path):
        raise ValueError("Model has multiple source paths. Cannot open as a text data.")
    out = model.with_value(model.source.read_text(), type=StandardType.TEXT)
    win._close_me(ui)
    return out


@register_function(
    menus=["tools/models"],
    title="Stack models ...",
    command_id="builtins:stack-models",
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
    menus=["tools/models"],
    types=[StandardType.MODELS],
    command_id="builtins:sort-model-list",
)
def sort_model_list(model: WidgetDataModel) -> Parametric:
    """Sort the model list."""

    def run_sort(
        descending: bool = False,
        sort_by: Literal["title", "type", "time"] = "title",
    ) -> WidgetDataModel:
        if sort_by == "title":

            def _sort_func(m: WidgetDataModel) -> str:
                return m.title
        elif sort_by == "type":

            def _sort_func(m: WidgetDataModel) -> str:
                return m.type
        elif sort_by == "time":

            def _sort_func(m: WidgetDataModel) -> datetime:
                if last := m.workflow.last():
                    return last.datetime
                return datetime(9999, 12, 31)
        else:
            raise ValueError(f"Invalid `sort_by` argument: {sort_by}")
        models = sorted(model.value, key=_sort_func, reverse=descending)
        return model.with_value(models, title=f"{model.title} sorted")

    return run_sort


@register_function(
    menus=["tools/models"],
    types=[StandardType.MODELS],
    command_id="builtins:filter-model-list",
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
        if isinstance(val := model.value, Mapping):
            models = val.values()
        else:
            models = val
        models_out = []
        for m in models:
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
            if model_type and not is_subtype(m.type, model_type):
                continue
            if title_contains and title_contains not in m.title:
                continue
            models_out.append(m)
        return model.with_value(models_out, title=f"{model.title} filtered")

    return run_filter


@register_function(
    types=[StandardType.WORKFLOW],
    menus=[],
    command_id="builtins:exec-workflow",
)
def exec_workflow(model: WidgetDataModel) -> None:
    """Execute the workflow."""
    if not isinstance(workflow := model.value, Workflow):
        raise TypeError(f"Expected a Workflow object but got {type(workflow)}")
    # NOTE: this function should not return the model and let the application process
    # it. The workflow of the output model should not be updated. Using workflow to
    # compute a new model is a special case in himena.
    workflow.compute(process_output=True)
    return None


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
    if is_subtype(model.type, StandardType.TEXT):
        value_str = str(value)
        nchars = len(value_str)
        nlines = len(value_str.splitlines())
        out = (
            f"<b>Number of characters:</b> {nchars}<br><b>Number of lines:</b> {nlines}"
        )
    elif is_subtype(model.type, StandardType.TABLE):
        out = _statistics_table(value)
    elif is_subtype(model.type, StandardType.DATAFRAME):
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
    elif is_subtype(model.type, StandardType.ARRAY):
        if not isinstance(value, np.ndarray):
            raise ValueError(f"Expected a numpy array but got {type(value)}")
        out = f"<b>Shape:</b> {value.shape}<br><b>Min:</b> {value.min()}<br><b>Max:</b> {value.max()}<br><b>Mean:</b> {value.mean()}<br><b>Std:</b> {value.std(ddof=1)}"
    elif is_subtype(model.type, StandardType.EXCEL):
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
        raise ValueError("Model does not have metadata.")
    if hasattr(meta, "_repr_html_"):
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
    menus=["tools"],
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
            type=StandardType.FUNCTION_PARTIAL,
            title=f"[Partial] {model.title}",
        )

    return run_partialize


def _statistics_table(value) -> str:
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
