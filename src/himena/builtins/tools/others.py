from pathlib import Path
import numpy as np
from himena._data_wrappers._dataframe import wrap_dataframe
from himena.plugins import register_function
from himena.types import WidgetDataModel, is_subtype
from himena.consts import StandardType
from himena.widgets import SubWindow, MainWindow


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
