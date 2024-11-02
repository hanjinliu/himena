from ndv import NDViewer
import numpy as np

from royalapp import new_window
from royalapp.consts import StandardTypes
from royalapp.qt import register_frontend_widget
from royalapp.types import WidgetDataModel

class MyNDViewer(NDViewer):
    @classmethod
    def from_model(cls, model: WidgetDataModel):
        return cls(model.value)

register_frontend_widget(StandardTypes.IMAGE, MyNDViewer)

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
