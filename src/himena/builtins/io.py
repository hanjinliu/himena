from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any
from himena.plugins import register_reader_provider, register_writer_provider
from himena.types import WidgetDataModel
from himena.consts import (
    StandardSubtypes,
    StandardTypes,
    BasicTextFileTypes,
    ConventionalTextFileNames,
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
    return None


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
    else:
        return None
