from pathlib import Path
from royalapp import new_window, register_reader_provider
from royalapp.qt import register_frontend_widget
from royalapp.types import WidgetDataModel
from wgpu.gui.qt import WgpuWidget
import imageio.v3 as iio
import pygfx as gfx

# `@register_frontend_widget` is a decorator that registers a widget class as a frontend
# widget for the given file type. The class must have an `import_data` method to convert
# file data to its instance.
@register_frontend_widget("image")
class WgpuImageWidget(WgpuWidget):
    @classmethod
    def import_data(cls, fd: WidgetDataModel):
        self = cls()
        renderer = gfx.WgpuRenderer(self)
        scene = gfx.Scene()
        image = gfx.Image(
            gfx.Geometry(grid=gfx.Texture(fd.value, dim=2)),
            gfx.ImageBasicMaterial(clim=(0, 255), pick_write=True),
        )
        scene.add(image)

        camera = gfx.OrthographicCamera(512, 512)
        camera.show_object(scene, view_dir=(0, 0, -1))
        camera.local.scale_y = -1

        def animate():
            renderer.render(scene, camera)
            self.request_draw()

        self.request_draw(animate)
        return self

@register_reader_provider
def my_reader_provider(file_path) -> WidgetDataModel:
    if Path(file_path).suffix not in {".png", ".jpg", ".jpeg"}:
        return None

    def _read_image(file_path):
        im = iio.imread(file_path)
        return WidgetDataModel(value=im, type="image", source=file_path)

    return _read_image

def main():
    ui = new_window()
    im = iio.imread("imageio:astronaut.png")
    ui.add_data(im, type="image", title="Astronaut")
    ui.show(run=True)

if __name__ == "__main__":
    main()
