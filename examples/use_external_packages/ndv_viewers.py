from ndv import NDViewer
import numpy as np

from himena import new_window
from himena.plugins import register_widget_class
from himena.types import WidgetDataModel
from himena.consts import StandardType

class MyNDViewer(NDViewer):
    def update_model(self, model: WidgetDataModel):
        return self.set_data(model.value)

register_widget_class(StandardType.IMAGE, MyNDViewer)

def main():
    ui = new_window()

    sample = np.random.default_rng(0).normal(size=(3, 100, 100))
    viewer0 = MyNDViewer(sample, channel_mode="composite")
    viewer1 = MyNDViewer(sample, channel_mode="mono")

    ui.add_widget(viewer0, title="Viewer-0")
    ui.add_widget(viewer1, title="Viewer-1")

    ui.show(run=True)

if __name__ == "__main__":
    main()
