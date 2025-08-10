from contextlib import suppress
import numpy as np
from qtpy import QtWidgets as QtW
import napari
from napari._qt.qt_resources import get_stylesheet
from napari._qt.qt_main_window import _QtMainWindow
from napari.qt import QtViewer

from himena import new_window, MainWindow
from himena.plugins import register_function
from himena.style import Theme

class MyViewer(QtW.QSplitter):
    def __init__(self, ui: MainWindow):
        super().__init__()
        self._tab_widget = QtW.QTabWidget()
        self._tab_widget.setSizePolicy(QtW.QSizePolicy.Minimum, QtW.QSizePolicy.Minimum)
        layout = QtW.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.viewer = napari.Viewer(show=False)
        self._qt_viewer = QtViewer(self.viewer)
        layout.addWidget(self._tab_widget)
        layout.addWidget(self._qt_viewer)
        self._tab_widget.addTab(self._qt_viewer.controls, "Layer Controls")
        self._tab_widget.addTab(self._qt_viewer.layers, "Layers")
        self._qt_viewer.setParent(self)

        # control widget
        control = QtW.QWidget()
        spacer = QtW.QWidget()
        spacer.setSizePolicy(QtW.QSizePolicy.Expanding, QtW.QSizePolicy.Preferred)
        self._qt_viewer.layerButtons.setSizePolicy(QtW.QSizePolicy.Preferred, QtW.QSizePolicy.Preferred)
        self._qt_viewer.viewerButtons.setSizePolicy(QtW.QSizePolicy.Preferred, QtW.QSizePolicy.Preferred)
        layout = QtW.QHBoxLayout(control)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(spacer)
        layout.addWidget(self._qt_viewer.layerButtons)
        layout.addWidget(self._qt_viewer.viewerButtons)
        self._control = control

        self._update_stylesheet(ui.theme.name)

    def _update_stylesheet(self, name: str):
        if name.startswith("dark"):
            _stylesheet = get_stylesheet("dark")
        else:
            _stylesheet = get_stylesheet("light")
        self.setStyleSheet(_stylesheet)
        self._control.setStyleSheet(_stylesheet)
        self._qt_viewer.canvas.background_color_override = "black" if name.startswith("dark") else "white"

    def control_widget(self):
        return self._control

    def widget_activated_callback(self):
        # reorder the current viewer
        with suppress(ValueError):
            inst = _QtMainWindow._instances
            inst.append(inst.pop(inst.index(self.viewer.window._qt_window)))

    def widget_closed_callback(self):
        with suppress(ValueError):
            _QtMainWindow._instances.remove(self.viewer.window._qt_window)

    def theme_changed_callback(self, theme: Theme):
        if theme.name.startswith("dark"):
            _stylesheet = get_stylesheet("dark")
        else:
            _stylesheet = get_stylesheet("light")
        self.setStyleSheet(_stylesheet)
        self.control_widget().setStyleSheet(_stylesheet)

    def size_hint(self):
        return 600, 400

@register_function(
    title="Open Napari Viewer",
    types=[],
    menus=["tools"],
    command_id="use_external_packages:napari_viewers",
)
def open_napari_viewers(ui: MainWindow) -> None:
    """Open a new napari viewer in the main window."""
    viewer0 = MyViewer(ui)
    tab = ui.add_tab("napari")
    tab.add_widget(viewer0, title="Viewer-0")

def main():
    ui = new_window()

    viewer0 = MyViewer(ui)
    viewer1 = MyViewer(ui)

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
