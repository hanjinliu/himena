from royalapp.qt import QMainWindow
from wgpu.gui.qt import WgpuWidget
import imageio.v3 as iio
import pygfx as gfx

def make_wgpu_canvas():
    canvas = WgpuWidget()
    renderer = gfx.WgpuRenderer(canvas)

    scene = gfx.Scene()

    im = iio.imread("imageio:astronaut.png")

    image = gfx.Image(
        gfx.Geometry(grid=gfx.Texture(im, dim=2)),
        gfx.ImageBasicMaterial(clim=(0, 255), pick_write=True),
    )
    scene.add(image)

    camera = gfx.OrthographicCamera(512, 512)
    camera.show_object(scene, view_dir=(0, 0, -1))
    camera.local.scale_y = -1

    def animate():
        renderer.render(scene, camera)
        canvas.request_draw()

    canvas.request_draw(animate)
    return canvas

def main():
    ui = QMainWindow()
    canvas = make_wgpu_canvas()
    ui.add_widget(canvas)
    ui.show(run=True)

if __name__ == "__main__":
    main()
