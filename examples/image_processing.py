import numpy as np
from scipy import ndimage as ndi
from typing import Annotated

from himena import new_window
from himena.plugins import register_function
from himena.types import WidgetDataModel, Parametric
from himena.consts import StandardType

@register_function(title="Gaussian Filter", types=StandardType.IMAGE)
def gaussian_filter(model: WidgetDataModel[np.ndarray]) -> Parametric:
    def func_gauss(sigma: float = 1.0) -> WidgetDataModel[np.ndarray]:
        im = model.value
        if im.ndim == 3:
            im = ndi.gaussian_filter(im, sigma=sigma, axes=(0, 1))
        else:
            im = ndi.gaussian_filter(im, sigma=sigma)
        return WidgetDataModel(
            value=im,
            type=StandardType.IMAGE,
            title=model.title + "-Gaussian",
        )
    return func_gauss

@register_function(title="Median Filter", types=StandardType.IMAGE)
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
            type=StandardType.IMAGE,
            title=model.title + "-Median",
        )
    return func_median

@register_function(title="Subtract images", types=StandardType.IMAGE)
def subtract_images() -> Parametric:
    def func_sub(
        a: Annotated[WidgetDataModel[np.ndarray], {"types": StandardType.IMAGE}],
        b: Annotated[WidgetDataModel[np.ndarray], {"types": StandardType.IMAGE}],
    ) -> WidgetDataModel[np.ndarray]:
        return WidgetDataModel(
            value=a.value - b.value,
            type=StandardType.IMAGE,
            title="result",
        )
    return func_sub

def main():
    ui = new_window()
    im = np.random.default_rng(123).normal(size=(100, 100))
    ui.add_object(im, type=StandardType.IMAGE, title="Noise")
    ui.show(run=True)

if __name__ == "__main__":
    main()
