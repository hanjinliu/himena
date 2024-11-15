from __future__ import annotations

import importlib
from pathlib import Path
from typing import TYPE_CHECKING, Any

from himena.plugins import register_reader_provider, register_writer_provider
from himena.types import WidgetDataModel
from himena.consts import (
    StandardSubtypes,
    StandardTypes,
    BasicTextFileTypes,
    ConventionalTextFileNames,
    ExcelFileTypes,
)

if TYPE_CHECKING:
    import numpy as np


def default_text_reader(file_path: Path) -> WidgetDataModel:
    """Read text file."""
    return WidgetDataModel(
        value=file_path.read_text(),
        type=StandardTypes.TEXT,
        source=file_path,
    )


def default_html_reader(file_path: Path) -> WidgetDataModel:
    return WidgetDataModel(
        value=file_path.read_text(),
        type=StandardSubtypes.HTML,
        source=file_path,
    )


def default_image_reader(file_path: Path) -> WidgetDataModel:
    """Read image file."""
    import numpy as np
    from PIL import Image

    arr = np.array(Image.open(file_path))

    return WidgetDataModel(
        value=arr,
        type=StandardTypes.IMAGE,
    )


def default_csv_reader(file_path: Path) -> WidgetDataModel:
    """Read CSV file."""
    import csv

    with open(file_path) as f:
        reader = csv.reader(f)
        data = list(reader)

    return WidgetDataModel(
        value=data,
        type=StandardTypes.TABLE,
    )


def default_tsv_reader(file_path: Path) -> WidgetDataModel:
    """Read TSV file."""
    import csv

    with open(file_path) as f:
        reader = csv.reader(f, delimiter="\t")
        data = list(reader)

    return WidgetDataModel(
        value=data,
        type=StandardTypes.TABLE,
    )


def default_excel_reader(file_path: Path) -> WidgetDataModel:
    """Read Excel file."""
    import openpyxl

    wb = openpyxl.load_workbook(file_path)
    data = {}
    for sheet in wb.sheetnames:
        ws = wb[sheet]
        sheet_data = []
        for row in ws.iter_rows(values_only=True):
            sheet_data.append([str(cell) if cell is not None else "" for cell in row])
        data[sheet] = sheet_data

    return WidgetDataModel(
        value=data,
        type=StandardTypes.EXCEL,
    )


@register_reader_provider(priority=-1)
def default_reader_provider(file_path: Path | list[Path]):
    """Get default reader."""
    if isinstance(file_path, list):
        return None
    if file_path.suffix in (".html", ".htm"):
        return default_html_reader
    elif file_path.suffix in BasicTextFileTypes:
        return default_text_reader
    elif file_path.suffix == ".csv":
        return default_csv_reader
    elif file_path.suffix == ".tsv":
        return default_tsv_reader
    elif file_path.suffix in {".png", ".jpg", ".jpeg"}:
        return default_image_reader
    elif file_path.name in ConventionalTextFileNames:
        return default_text_reader
    elif file_path.suffix in ExcelFileTypes:
        return default_excel_reader
    return None


class DataFrameReader:
    def __init__(self, module: str, method: str, kwargs: dict[str, Any]):
        self._module = module
        self._method = method
        self._kwargs = kwargs

    def __repr__(self):
        return f"{self.__class__.__name__}<{self._module}.{self._method}>"

    def __call__(self, file_path: Path) -> WidgetDataModel:
        mod = importlib.import_module(self._module)
        method = getattr(mod, self._method)
        df = method(file_path, **self._kwargs)
        return WidgetDataModel(value=df, type=StandardTypes.DATAFRAME)


@register_reader_provider(priority=-5)
def pandas_reader_provider(file_path: Path) -> WidgetDataModel:
    """Read dataframe using pandas."""
    if file_path.suffix in (".html", ".htm"):
        _reader = "pandas", "read_html", {}
    elif file_path.suffix == ".csv":
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
    return DataFrameReader(*_reader)


@register_reader_provider(priority=-5)
def polars_reader_provider(file_path: Path) -> WidgetDataModel:
    """Read dataframe using polars."""
    if file_path.suffix == ".csv":
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
    return DataFrameReader(*_reader)


@register_reader_provider(priority=-5)
def pyarrow_reader_provider(file_path: Path) -> WidgetDataModel:
    """Read dataframe using pyarrow."""
    if file_path.suffix == ".csv":
        _reader = "pyarrow.csv", "read_csv", {}
    elif file_path.suffix == ".feather":
        _reader = "pyarrow.feather", "read_feather", {}
    elif file_path.suffix in (".parquet", ".pq"):
        _reader = "pyarrow.parquet", "read_table", {}
    else:
        return None
    return DataFrameReader(*_reader)


def default_text_writer(model: WidgetDataModel[str], path: Path) -> None:
    """Write text file."""
    with open(path, "w") as f:
        f.write(model.value)
    return None


def default_csv_writer(model: WidgetDataModel[list[list[str]]], path: Path) -> None:
    """Write CSV file."""
    import csv

    with open(path, "w") as f:
        writer = csv.writer(f)
        writer.writerows(model.value)


def default_image_writer(model: WidgetDataModel[np.ndarray], path: Path) -> None:
    """Write image file."""
    from PIL import Image

    Image.fromarray(model.value).save(path)
    return None


def default_parameter_writer(
    model: WidgetDataModel[dict[str, Any]], path: Path
) -> None:
    """Write parameters to a json file."""
    import json

    with open(path, "w") as f:
        json.dump(model.value, f)


def default_excel_writer(
    model: WidgetDataModel[dict[str, list[list[str]]]],
    path: Path,
) -> None:
    """Write Excel file."""
    import openpyxl
    from openpyxl.worksheet._write_only import WriteOnlyWorksheet

    wb = openpyxl.Workbook(write_only=True)
    for sheet_name, table in model.value.items():
        ws: WriteOnlyWorksheet = wb.create_sheet(sheet_name)
        for row in table:
            ws.append(row)
    wb.save(path)
    return None


@register_writer_provider(priority=-1)
def default_writer_provider(model: WidgetDataModel):
    """Get default writer."""
    if model.type is None:
        return None
    if model.is_subtype_of(StandardTypes.TEXT):
        return default_text_writer
    elif model.is_subtype_of(StandardTypes.TABLE):
        return default_csv_writer
    elif model.is_subtype_of(StandardTypes.IMAGE):
        return default_image_writer
    elif model.is_subtype_of(StandardTypes.PARAMETERS):
        return default_parameter_writer
    elif model.is_subtype_of(StandardTypes.EXCEL):
        return default_excel_writer
    else:
        return None
