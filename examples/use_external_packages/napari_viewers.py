import numpy as np
from qtpy import QtWidgets as QtW
import napari
from napari.qt import QtViewer

from himena import new_window

class MyViewer(QtW.QWidget):
    def __init__(self):
        super().__init__()
        layout = QtW.QVBoxLayout()
        self.viewer = napari.Viewer(show=False)
        self._qt_viewer = QtViewer(self.viewer)
        self._toggle_btn = QtW.QPushButton("2D/3D")
        self._toggle_btn.clicked.connect(self._on_toggle)
        layout.addWidget(self._toggle_btn)
        layout.addWidget(self._qt_viewer)
        self._qt_viewer.setParent(self)
        self.setLayout(layout)
        self.resize(300, 200)

    def _on_toggle(self):
        ndisplay = self.viewer.dims.ndisplay
        if ndisplay == 2:
            self.viewer.dims.ndisplay = 3
        else:
            self.viewer.dims.ndisplay = 2

def main():
    ui = new_window()

    viewer0 = MyViewer()
    viewer1 = MyViewer()

    viewer0.viewer.open_sample("napari", "brain")
    viewer1.viewer.add_points(
        np.random.normal(scale=(20, 30, 15), size=(80, 3)),
        size=5,
        shading="spherical",
        out_of_slice_display=True,
    )

    ui.add_widget(viewer0, title="Viewer-0")
    ui.add_widget(viewer1, title="Viewer-1")

    ui.show(run=True)

if __name__ == "__main__":
    main()
