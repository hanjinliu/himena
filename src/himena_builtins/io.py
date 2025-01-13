from __future__ import annotations

from pathlib import Path
from himena.plugins import register_reader_provider, register_writer_provider
from himena.types import WidgetDataModel
from himena_builtins import _io
from himena.consts import (
    StandardType,
    BasicTextFileTypes,
    ConventionalTextFileNames,
    ExcelFileTypes,
)


@register_reader_provider(priority=50)
def default_reader_provider(file_path: Path | list[Path]):
    """Get default reader."""
    if isinstance(file_path, list):
        return _io.default_file_list_reader, StandardType.MODELS
    if file_path.suffix == ".csv":
        return _io.default_csv_reader, StandardType.TABLE
    elif file_path.suffix == ".tsv":
        return _io.default_tsv_reader, StandardType.TABLE
    elif file_path.suffix in {".png", ".jpg", ".jpeg"}:
        return _io.default_image_reader, StandardType.IMAGE
    elif file_path.suffix == ".json":
        if file_path.suffixes == [".plot", ".json"]:
            return _io.default_plot_reader, StandardType.PLOT
        elif file_path.suffixes == [".roi", ".json"]:
            return _io.default_roi_reader, StandardType.ROIS
        elif file_path.suffixes == [".workflow", ".json"]:
            return _io.default_workflow_reader, StandardType.WORKFLOW
        else:
            return _io.default_text_reader, StandardType.TEXT
    elif file_path.suffix in BasicTextFileTypes:
        return _io.default_text_reader, StandardType.TEXT
    elif file_path.name in ConventionalTextFileNames:
        return _io.default_text_reader, StandardType.TEXT
    elif file_path.suffix in ExcelFileTypes:
        return _io.default_excel_reader, StandardType.EXCEL
    elif file_path.suffix == ".npy":
        return _io.default_array_reader, StandardType.ARRAY
    elif file_path.suffix in {".parquet", ".pq"}:
        return _io.DataFrameReader("pandas", "read_parquet", {}), StandardType.DATAFRAME
    elif file_path.suffix == ".feather":
        return _io.DataFrameReader("pandas", "read_feather", {}), StandardType.DATAFRAME
    elif file_path.suffix == ".pickle":
        return _io.default_pickle_reader, StandardType.ANY
    elif file_path.suffix == "":
        return _io.default_file_list_reader, StandardType.MODELS
    elif file_path.suffix == ".zip":
        return _io.default_zip_reader, StandardType.MODELS
    return None


@register_reader_provider(priority=-100)
def read_as_text_anyway_provider(file_path: Path):
    return _io.default_plain_text_reader, StandardType.TEXT


@register_reader_provider(priority=0)
def read_as_unknown_provider(file_path: Path):
    return _io.fallback_reader


@register_reader_provider(priority=-50)
def polars_reader_provider(file_path: Path):
    """Read dataframe using polars."""
    if isinstance(file_path, list):
        return None
    elif file_path.suffix in (".csv", ".txt"):
        _reader = "polars", "read_csv", {}
    elif file_path.suffix == ".tsv":
        _reader = "polars", "read_csv", {"sep": "\t"}
    elif file_path.suffix == ".feather":
        _reader = "polars", "read_ipc", {}
    elif file_path.suffix == ".json":
        _reader = "polars", "read_json", {}
    elif file_path.suffix in (".parquet", ".pq"):
        _reader = "polars", "read_parquet", {}
    else:
        return None
    return _io.DataFrameReader(*_reader), StandardType.DATAFRAME


@register_reader_provider(priority=-50)
def pandas_reader_provider(file_path: Path):
    """Read dataframe using pandas."""
    if file_path.suffix in (".html", ".htm"):
        _reader = "pandas", "read_html", {}
    elif file_path.suffix in (".csv", ".txt"):
        _reader = "pandas", "read_csv", {}
    elif file_path.suffix == ".tsv":
        _reader = "pandas", "read_csv", {"sep": "\t"}
    elif file_path.suffix == ".json":
        _reader = "pandas", "read_json", {}
    elif file_path.suffix in (".pq", ".parquet"):
        _reader = "pandas", "read_parquet", {}
    elif file_path.suffix == ".feather":
        _reader = "pandas", "read_feather", {}
    else:
        return None
    return _io.DataFrameReader(*_reader), StandardType.DATAFRAME


@register_reader_provider(priority=-50)
def polars_plot_reader_provider(file_path: Path):
    out = polars_reader_provider(file_path)
    if out is None:
        return None
    return out[0].as_plot_type(), StandardType.DATAFRAME_PLOT


@register_reader_provider(priority=-50)
def pandas_plot_reader_provider(file_path: Path):
    out = pandas_reader_provider(file_path)
    if out is None:
        return None
    return out[0].as_plot_type(), StandardType.DATAFRAME_PLOT


@register_writer_provider(priority=50)
def default_writer_provider(model: WidgetDataModel, path: Path):
    """Get default writer."""
    if model.type is None:
        return None
    if model.is_subtype_of(StandardType.TEXT):
        return _io.default_text_writer
    elif model.is_subtype_of(StandardType.TABLE):
        return _io.default_table_writer
    elif model.is_subtype_of(StandardType.IMAGE):
        return _io.default_image_writer
    elif model.is_subtype_of(StandardType.DICT):
        return _io.default_dict_writer
    elif model.is_subtype_of(StandardType.EXCEL):
        return _io.default_excel_writer
    elif model.is_subtype_of(StandardType.ARRAY):
        return _io.default_array_writer
    elif model.is_subtype_of(StandardType.PLOT):
        return _io.default_plot_writer
    elif model.is_subtype_of(StandardType.ROIS):
        return _io.default_roi_writer
    elif model.is_subtype_of(StandardType.DATAFRAME):
        return _io.default_dataframe_writer
    elif model.is_subtype_of(StandardType.MODELS):
        return _io.default_models_writer
    elif model.is_subtype_of(StandardType.WORKFLOW):
        return _io.default_workflow_writer
    else:
        return None


@register_writer_provider(priority=-50)
def write_as_pickle_anyway_provider(model: WidgetDataModel, path: Path):
    return _io.default_pickle_writer
