import numpy as np
import fastplotlib as fpl
from cmap import Colormap
from himena.plugins import register_widget_class, protocol_override
from himena import WidgetDataModel, StandardType, new_window
from himena.standards.model_meta import ImageMeta

@register_widget_class(StandardType.IMAGE)
class FastplotlibImageView(fpl.Figure):
    def __init__(self):
        super().__init__()
        self._image_graphic: fpl.ImageGraphic | None = None
        self._native_widget = self.show()

    @protocol_override
    def update_model(self, model: WidgetDataModel):
        if self._image_graphic is not None:
            self._image_graphic.data = model.value
        else:
            self._image_graphic = self[0, 0].add_image(model.value, cmap="gray")

        # himena has an ImageMeta standard. By using it, widgets can inherit richer
        # information. There are more fields that can be set but here we just exemplify
        # how to do that.
        if isinstance(meta := model.metadata, ImageMeta):
            if meta.colormap is not None:
                self._image_graphic.cmap = Colormap(meta.colormap).name.split(":")[-1]
            if meta.interpolation is not None:
                self._image_graphic.interpolation = meta.interpolation
            if meta.contrast_limits is not None:
                self._image_graphic.vmin, self._image_graphic.vmax = meta.contrast_limits

    @protocol_override
    def to_model(self) -> WidgetDataModel:
        # To make the widget interchangable with other plugins, it's better to prepare
        # a metadata properly.  There are more fields that can be set but here we just
        # exemplify how to do that.
        meta = ImageMeta(
            colormap=self._image_graphic.cmap,
            interpolation=self._image_graphic.interpolation,
            contrast_limits=(self._image_graphic.vmin, self._image_graphic.vmax),
        )
        return WidgetDataModel(
            value=self._image_graphic.data.value, # the numpy array
            type=StandardType.IMAGE,
            metadata=meta,
        )

    @protocol_override
    def native_widget(self):
        return self._native_widget

    @protocol_override
    def size_hint(self) -> tuple[int, int]:
        return 320, 320

    @protocol_override
    def window_added_callback(self):
        # this function will be called when the widget is added to a window
        self[0, 0].auto_scale()

if __name__ == "__main__":
    ui = new_window()
    ui.add_data(np.random.rand(100, 100), type=StandardType.IMAGE)
    ui.show(run=True)
