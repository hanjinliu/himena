from __future__ import annotations

from pathlib import Path
from royalapp.io import register_writer_provider
from royalapp.types import WidgetDataModel
from royalapp.consts import StandardTypes, BasicTextFileTypes
from royalapp import register_reader_provider


def _read_text(file_path: Path) -> WidgetDataModel:
    """Read text file."""
    with open(file_path) as f:
        return WidgetDataModel(
            value=f.read(),
            type=StandardTypes.TEXT,
            source=Path(file_path),
        )


def _read_simple_image(file_path: Path) -> WidgetDataModel:
    """Read image file."""
    import numpy as np
    from PIL import Image

    arr = np.array(Image.open(file_path))

    return WidgetDataModel(
        value=arr,
        type=StandardTypes.IMAGE,
        source=Path(file_path),
    )


def _read_csv(file_path: Path) -> WidgetDataModel:
    """Read CSV file."""
    import csv

    with open(file_path) as f:
        reader = csv.reader(f)
        data = list(reader)

    return WidgetDataModel(
        value=data,
        type=StandardTypes.TABLE,
        source=Path(file_path),
    )


def _read_tsv(file_path: Path) -> WidgetDataModel:
    """Read TSV file."""
    import csv

    with open(file_path) as f:
        reader = csv.reader(f, delimiter="\t")
        data = list(reader)

    return WidgetDataModel(
        value=data,
        type=StandardTypes.TABLE,
        source=Path(file_path),
    )


@register_reader_provider
def default_reader_provider(file_path: Path | list[Path]):
    """Get default reader."""
    if isinstance(file_path, list):
        return None
    if file_path.suffix in BasicTextFileTypes:
        return _read_text
    elif file_path.suffix == ".csv":
        return _read_csv
    elif file_path.suffix == ".tsv":
        return _read_tsv
    elif file_path.suffix in {".png", ".jpg", ".jpeg"}:
        return _read_simple_image
    return None


def _write_text(file_data: WidgetDataModel[str]) -> None:
    """Write text file."""
    if file_data.source is None:
        return None
    with open(file_data.source, "w") as f:
        f.write(file_data.value)
    return None


@register_writer_provider
def default_writer_provider(file_data: WidgetDataModel):
    """Get default writer."""
    if file_data.source.suffix in BasicTextFileTypes:
        return _write_text
    else:
        return None
