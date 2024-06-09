from ndv import NDViewer, data

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

    sample = data.cells3d()
    viewer0 = MyNDViewer(sample, channel_mode="composite")
    viewer1 = MyNDViewer(sample, channel_mode="mono")

    ui.add_widget(viewer0, title="Viewer-0")
    ui.add_widget(viewer1, title="Viewer-1")

    ui.show(run=True)

if __name__ == "__main__":
    main()
