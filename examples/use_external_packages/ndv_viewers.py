from ndv import ArrayViewer
import numpy as np

from himena import new_window
from himena.plugins import register_widget_class
from himena.types import WidgetDataModel
from himena.consts import StandardType

class MyNDViewer(ArrayViewer):
    def update_model(self, model: WidgetDataModel):
        self.data = model.value

    def native_widget(self):
        return self._view._qwidget

register_widget_class(StandardType.IMAGE, MyNDViewer)

def main():
    ui = new_window()

    sample = np.random.default_rng(0).normal(size=(3, 100, 100))
    viewer0 = MyNDViewer(sample, channel_mode="composite")
    viewer1 = MyNDViewer(sample, channel_mode="grayscale")

    ui.add_widget(viewer0, title="Viewer-0")
    ui.add_widget(viewer1, title="Viewer-1")

    ui.show(run=True)

if __name__ == "__main__":
    main()
