from pathlib import Path

import numpy as np
from royalapp import (
    new_window,
    register_reader_provider,
    register_writer_provider,
    WidgetDataModel
)
from royalapp.qt import register_frontend_widget
from royalapp.plugins import get_plugin_interface
from wgpu.gui.qt import WgpuWidget
import imageio.v3 as iio
import pygfx as gfx

# `@register_frontend_widget` is a decorator that registers a widget class as a frontend
# widget for the given file type. The class must have an `from_model` method to convert
# data model to its instance. By further providing `to_model` method, the widget can
# be converted back to data model.
@register_frontend_widget("image")
class WgpuImageWidget(WgpuWidget):
    def __init__(self, model: WidgetDataModel[np.ndarray]):
        super().__init__()
        self._model = model

    @classmethod
    def from_model(cls, model: WidgetDataModel[np.ndarray]):
        self = cls(model)
        renderer = gfx.WgpuRenderer(self)
        scene = gfx.Scene()
        image = gfx.Image(
            gfx.Geometry(grid=gfx.Texture(model.value, dim=2)),
            gfx.ImageBasicMaterial(clim=(0, 255), pick_write=True),
        )
        scene.add(image)

        camera = gfx.OrthographicCamera(model.value.shape[0], model.value.shape[1])
        camera.show_object(scene, view_dir=(0, 0, -1))
        camera.local.scale_y = -1

        def animate():
            renderer.render(scene, camera)
            self.request_draw()

        self.request_draw(animate)
        return self

    def to_model(self) -> WidgetDataModel:
        return WidgetDataModel(value=self._model.value, type="image", title=self._model.title)

# `@register_reader_provider` is a decorator that registers a function as one that
# provides a reader for the given file path.
@register_reader_provider
def my_reader_provider(file_path):
    if Path(file_path).suffix not in {".png", ".jpg", ".jpeg"}:
        return None

    def _read_image(file_path):
        im = iio.imread(file_path)
        return WidgetDataModel(value=im, type="image")

    return _read_image

# `@register_writer_provider` is a decorator that registers a function as one that
# provides a write for the given data model.
@register_writer_provider
def my_writer_provider(model: WidgetDataModel, path: Path):
    if not isinstance(model.value, np.ndarray):
        return None
    if path.suffix not in {".png", ".jpg", ".jpeg"}:
        return None
    def _write_image(model: WidgetDataModel):
        iio.imwrite(path, model.value)
    return _write_image

interf = get_plugin_interface("tools/image_processing")

@interf.register_function(title="Gaussian Filter", types="image")
def gaussian_filter(model: WidgetDataModel[np.ndarray]) -> WidgetDataModel[np.ndarray]:
    from scipy import ndimage as ndi

    im = model.value
    if im.ndim == 3:
        im = ndi.gaussian_filter(im, sigma=3, axes=(0, 1))
    else:
        im = ndi.gaussian_filter(im, sigma=3)
    return WidgetDataModel(value=im, type="image", title=model.title + "-Gaussian")

@interf.register_function(title="Invert", types="image")
def invert(model: WidgetDataModel) -> WidgetDataModel:
    return WidgetDataModel(value=-model.value, type="image", title=model.title + "-Inverted")


def main():
    ui = new_window(plugins=[interf])
    im = iio.imread("imageio:astronaut.png")
    ui.add_data(im, type="image", title="Astronaut")
    ui.show(run=True)

if __name__ == "__main__":
    main()
