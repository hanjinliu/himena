from pathlib import Path
from dataclasses import dataclass
from typing import Any
import numpy as np
from tifffile import TiffFile, imwrite
from himena import (
    WidgetDataModel,
    new_window,
)
from himena.plugins import (
    register_reader_provider,
    register_writer_provider,
    register_widget_class,
)
from himena.builtins.qt.widgets import QDefaultImageView

TIFF_TYPE = "tiff"

@dataclass
class ImageAndMetadata:
    """A class for a image data with a metadata"""
    image: np.ndarray
    metadata: dict[str, Any]

# Define a function
@register_reader_provider
def read_tiff_provider(path: Path):
    if path.suffix not in (".tif", ".tiff"):
        return None
    def read(path: Path):
        with TiffFile(path, mode="r") as tif:
            ijmeta = tif.imagej_metadata
            if ijmeta is None:
                ijmeta = {}
            img_data = ImageAndMetadata(tif.asarray(), ijmeta)
        return WidgetDataModel(
            value=img_data,
            type=TIFF_TYPE,
            title=path.name
        )
    return read

@register_writer_provider
def write_tiff_provider(model: WidgetDataModel[ImageAndMetadata], path: Path):
    if model.type is not TIFF_TYPE:
        return None
    def write(model: WidgetDataModel[ImageAndMetadata]):
        return imwrite(path, model.value.image, **model.value.metadata)
    return write

@register_widget_class(TIFF_TYPE)
class QTiffView(QDefaultImageView):
    def update_model(self, model: WidgetDataModel[ImageAndMetadata]):
        simple_model = WidgetDataModel(value=model.value.image, type=TIFF_TYPE)
        super().update_model(simple_model)
        self._tiff_model = model

    def to_model(self) -> WidgetDataModel:
        return self._tiff_model


if __name__ == "__main__":
    ui = new_window()
    ui.show(run=True)
