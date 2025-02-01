from pathlib import Path
from tifffile import TiffFile, imwrite
from himena import (
    WidgetDataModel,
    new_window,
)
from himena.consts import StandardType
from himena.plugins import (
    register_reader_plugin,
    register_writer_plugin,
)
from himena.standards.model_meta import ImageMeta

@register_reader_plugin
def read_tiff_provider(path: Path):
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

@read_tiff_provider.define_matcher
def _(path: Path):
    if path.suffix in (".tif", ".tiff"):
        return StandardType.IMAGE
    return None

@register_writer_plugin
def write_tiff(model: WidgetDataModel, path: Path):
    return imwrite(path, model.value)

@write_tiff.define_matcher
def _(model: WidgetDataModel, path: Path):
    return model.type == StandardType.IMAGE and path.suffix in (".tif", ".tiff")

if __name__ == "__main__":
    ui = new_window()
    ui.show(run=True)
