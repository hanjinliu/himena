from royalapp import new_window
from royalapp.plugins import get_plugin_interface
from royalapp.types import WidgetDataModel, Parametric
import numpy as np
from scipy import ndimage as ndi

interf = get_plugin_interface("tools/image_processing")

@interf.register_function(title="Gaussian Filter", types="image")
def gaussian_filter(model: WidgetDataModel[np.ndarray]) -> Parametric:
    def func(sigma: float = 1.0) -> WidgetDataModel[np.ndarray]:
        im = model.value
        if im.ndim == 3:
            im = ndi.gaussian_filter(im, sigma=sigma, axes=(0, 1))
        else:
            im = ndi.gaussian_filter(im, sigma=sigma)
        return WidgetDataModel(value=im, type="image", title=model.title + "-Gaussian")
    return func

def main():
    ui = new_window(plugins=[interf])
    im = np.random.default_rng(123).normal(size=(100, 100))
    ui.add_data(im, type="image", title="Noise")
    ui.show(run=True)

if __name__ == "__main__":
    main()
