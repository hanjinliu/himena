from __future__ import annotations

from pathlib import Path
from himena.plugins import register_reader_provider, register_writer_provider
from himena.types import WidgetDataModel
from himena.builtins import _io
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
        return None
    if file_path.suffix == ".csv":
        return _io.default_csv_reader
    elif file_path.suffix == ".tsv":
        return _io.default_tsv_reader
    elif file_path.suffix in {".png", ".jpg", ".jpeg"}:
        return _io.default_image_reader
    elif file_path.suffixes == [".plot", ".json"]:
        return _io.default_plot_reader
    elif file_path.suffix in BasicTextFileTypes:
        return _io.default_text_reader
    elif file_path.name in ConventionalTextFileNames:
        return _io.default_text_reader
    elif file_path.suffix in ExcelFileTypes:
        return _io.default_excel_reader
    elif file_path.suffix == ".npy":
        return _io.default_array_reader
    elif file_path.suffix in {".parquet", ".pq"}:
        return _io.DataFrameReader("pandas", "read_parquet", {})
    elif file_path.suffix == ".feather":
        return _io.DataFrameReader("pandas", "read_feather", {})
    elif file_path.suffix == ".pickle":
        return _io.default_pickle_reader
    return None


@register_reader_provider(priority=-100)
def read_as_text_anyway_provider(file_path: Path):
    return _io.default_text_reader


@register_reader_provider(priority=0)
def read_as_unknown_provider(file_path: Path):
    return _io.fallback_reader


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
    return _io.DataFrameReader(*_reader)


@register_reader_provider(priority=-50)
def polars_reader_provider(file_path: Path) -> WidgetDataModel:
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
    return _io.DataFrameReader(*_reader)


@register_writer_provider(priority=50)
def default_writer_provider(model: WidgetDataModel):
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
    elif model.is_subtype_of(StandardType.DATAFRAME):
        return _io.default_dataframe_writer
    else:
        return None


@register_writer_provider(priority=-50)
def write_as_pickle_anyway_provider(model: WidgetDataModel):
    return _io.default_pickle_writer
