from pathlib import Path
from tifffile import TiffFile, imwrite
from himena import (
    WidgetDataModel,
    new_window,
)
from himena.consts import StandardType
from himena.plugins import (
    register_reader_provider,
    register_writer_provider,
)
from himena.standards.model_meta import ImageMeta

@register_reader_provider
def read_tiff_provider(path: Path):
    if path.suffix not in (".tif", ".tiff"):
        return None
    return read_tif

def read_tif(path: Path):
    with TiffFile(path, mode="r") as tif:
        ijmeta = tif.imagej_metadata
        if ijmeta is None:
            ijmeta = {}
        img_data = tif.asarray()
        series0 = tif.series[0]
        try:
            axes = series0.axes.lower()
        except Exception:
            axes = None
    return WidgetDataModel(
        value=img_data,
        type=StandardType.IMAGE,
        title=path.name,
        metadata=ImageMeta(axes=axes)
    )

@register_writer_provider
def write_tiff_provider(model: WidgetDataModel, path: Path):
    if model.type is not StandardType.IMAGE:
        return None
    return write_tif

def write_tif(model: WidgetDataModel, path: Path):
    return imwrite(path, model.value)

if __name__ == "__main__":
    ui = new_window()
    ui.show(run=True)
