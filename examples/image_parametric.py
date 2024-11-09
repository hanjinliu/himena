import numpy as np
from scipy import ndimage as ndi
from typing import Annotated

from himena import new_window
from himena.plugins import get_plugin_interface
from himena.types import WidgetDataModel, Parametric
from himena.consts import StandardTypes

interf = get_plugin_interface()

@interf.register_function(title="Gaussian Filter", types=StandardTypes.IMAGE)
def gaussian_filter(model: WidgetDataModel[np.ndarray]) -> Parametric:
    def func_gauss(sigma: float = 1.0) -> WidgetDataModel[np.ndarray]:
        im = model.value
        if im.ndim == 3:
            im = ndi.gaussian_filter(im, sigma=sigma, axes=(0, 1))
        else:
            im = ndi.gaussian_filter(im, sigma=sigma)
        return WidgetDataModel(
            value=im,
            type=StandardTypes.IMAGE,
            title=model.title + "-Gaussian",
        )
    return func_gauss

@interf.register_function(title="Median Filter", types=StandardTypes.IMAGE)
def median_filter(model: WidgetDataModel[np.ndarray]) -> Parametric:
    def func_median(radius: int = 1) -> WidgetDataModel[np.ndarray]:
        im = model.value
        footprint = np.ones((radius * 2 + 1, radius * 2 + 1), dtype=int)
        if im.ndim == 3:
            im = ndi.median_filter(im, footprint=footprint, axes=(0, 1))
        else:
            im = ndi.median_filter(im, footprint=footprint)
        return WidgetDataModel(
            value=im,
            type=StandardTypes.IMAGE,
            title=model.title + "-Median",
        )
    return func_median

@interf.register_function(title="Subtract images", types=StandardTypes.IMAGE)
def subtract_images() -> Parametric:
    def func_sub(
        a: Annotated[WidgetDataModel[np.ndarray], {"types": StandardTypes.IMAGE}],
        b: Annotated[WidgetDataModel[np.ndarray], {"types": StandardTypes.IMAGE}],
    ) -> WidgetDataModel[np.ndarray]:
        return WidgetDataModel(
            value=a.value - b.value,
            type=StandardTypes.IMAGE,
            title="result",
        )
    return func_sub

def main():
    ui = new_window(plugins=[interf])
    im = np.random.default_rng(123).normal(size=(100, 100))
    ui.add_data(im, type=StandardTypes.IMAGE, title="Noise")
    ui.show(run=True)

if __name__ == "__main__":
    main()
