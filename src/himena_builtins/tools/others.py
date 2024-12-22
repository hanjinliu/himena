from pathlib import Path
import html
from typing import Mapping
import warnings
import numpy as np
from himena._data_wrappers._dataframe import wrap_dataframe
from himena.plugins import register_function, configure_gui
from himena.types import Parametric, WidgetDataModel, is_subtype
from himena.consts import StandardType, MonospaceFontFamily
from himena.widgets import SubWindow, MainWindow
from himena._utils import unwrap_lazy_model


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
    menus=["tools"],
    title="Merge models ...",
    command_id="builtins:merge-models",
)
def merge_models() -> Parametric:
    """Merge models as an model list."""

    def run_merge_models(models: list[WidgetDataModel]) -> WidgetDataModel:
        return WidgetDataModel(
            value=models,
            type=StandardType.MODELS,
            title="Merged models",
        )

    return run_merge_models


@register_function(
    menus=["tools/models"],
    types=[StandardType.MODELS],
    command_id="builtins:filter-model-list",
)
def filter_model_list(model: WidgetDataModel) -> Parametric:
    """Filter the list of models."""

    @configure_gui
    def run_filter(
        model_type: str = "",
        title_contains: str = "",
        unwrap_lazy_objects: bool = True,
    ) -> WidgetDataModel:
        """Filter the list of models.

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
        return WidgetDataModel(
            value=models_out,
            type=StandardType.MODELS,
            title=f"{model.title} filtered",
        )

    return run_filter


@register_function(
    types=[
        StandardType.TEXT,
        StandardType.TABLE,
        StandardType.DATAFRAME,
        StandardType.ARRAY,
        StandardType.EXCEL,
    ],
    menus=["tools"],
    command_id="builtins:show-statistics",
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
    )


@register_function(
    menus=["tools"],
    command_id="builtins:show-metadata",
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
    )


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
