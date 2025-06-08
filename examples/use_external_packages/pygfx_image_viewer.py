import numpy as np
from himena import new_window, WidgetDataModel
from himena.consts import StandardType
from himena.plugins import (
    register_function,
    register_widget_class,
    validate_protocol,
)
from wgpu.gui.qt import WgpuWidget
import imageio.v3 as iio
import pygfx as gfx

@register_widget_class(StandardType.IMAGE)
class WgpuImageWidget(WgpuWidget):
    def __init__(self):
        super().__init__()
        self._renderer = gfx.WgpuRenderer(self)
        self._scene = gfx.Scene()

        self._arr = None
        self._current_image = None
        self._camera = gfx.OrthographicCamera()
        self._controller = gfx.PanZoomController(self._camera, register_events=self._renderer)
        self._camera.local.scale_y = -1

        self.request_draw(self._animate)

    def _animate(self):
        self._renderer.render(self._scene, self._camera)
        self.request_draw(self._animate)

    def set_image(self, arr):
        if self._current_image is not None:
            self._scene.remove(self._current_image)
        image = gfx.Image(
            gfx.Geometry(grid=gfx.Texture(arr, dim=2)),
            gfx.ImageBasicMaterial(clim=(0, 255), pick_write=True),
        )
        self._scene.add(image)
        self._current_image = image
        self._arr = arr

    @validate_protocol
    def update_model(self, model: WidgetDataModel[np.ndarray]):
        self._camera.width = model.value.shape[1]
        self._camera.height = model.value.shape[0]
        return self.set_image(model.value)

    @validate_protocol
    def to_model(self) -> WidgetDataModel:
        return WidgetDataModel(value=self._arr, type=StandardType.IMAGE)

    @validate_protocol
    def size_hint(self) -> tuple[int, int]:
        return 400, 320

    @validate_protocol
    def widget_added_callback(self):
        self._camera.show_object(self._current_image)

@register_function(title="Gaussian Filter", types=StandardType.IMAGE, menus="tools/image_processing")
def gaussian_filter(model: WidgetDataModel[np.ndarray]) -> WidgetDataModel[np.ndarray]:
    from scipy import ndimage as ndi

    im = model.value
    if im.ndim == 3:
        im = ndi.gaussian_filter(im, sigma=3, axes=(0, 1))
    else:
        im = ndi.gaussian_filter(im, sigma=3)
    return WidgetDataModel(value=im, type=StandardType.IMAGE, title=model.title + "-Gaussian")

@register_function(title="Invert", types=StandardType.IMAGE, menus="tools/image_processing")
def invert(model: WidgetDataModel) -> WidgetDataModel:
    return WidgetDataModel(value=-model.value, type=StandardType.IMAGE, title=model.title + "-Inverted")


def main():
    ui = new_window()
    im = iio.imread("imageio:astronaut.png")
    ui.add_object(im, type=StandardType.IMAGE, title="Astronaut")
    ui.show(run=True)

if __name__ == "__main__":
    main()
