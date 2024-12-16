# This example shows how to use the vedo canvas in himena.
# The "QVedoCanvas" will be used for the model type "mesh".
# Calling register_function adds a new menu item to the "File > Samples > Vedo", which
# loads a vedo sample data.

import vedo

from typing import TYPE_CHECKING
from qtpy import QtWidgets as QtW, QtGui

from himena import new_window
from himena.types import WidgetDataModel
from himena.consts import StandardType
from himena.plugins import register_widget_class, register_function

if TYPE_CHECKING:
    from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
else:
    from vtk.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor

class QVedoCanvas(QtW.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        _layout = QtW.QVBoxLayout()
        _layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(_layout)
        self._vtk_widget = QVTKRenderWindowInteractor(parent=self)
        self._plt = vedo.Plotter(qt_widget=self._vtk_widget, bg="bb", axes=0)
        self._plt.show()

        _layout.addWidget(self._vtk_widget)

    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
        self._vtk_widget.close()
        return super().closeEvent(a0)

    def update_model(self, model: WidgetDataModel):
        mesh = model.value
        if isinstance(mesh, vedo.Mesh):
            vedo_mesh = mesh
        else:
            vedo_mesh = vedo.Mesh(mesh)
        self._plt.clear()
        self._plt.add(vedo_mesh)
        self._plt.reset_camera()

    def to_model(self) -> WidgetDataModel:
        return WidgetDataModel(
            value=self._plt.actors[0],
            type=StandardType.MESH,
        )

register_widget_class(StandardType.MESH, QVedoCanvas)

@register_function(
    menus="file/new/vedo",
    title="load man.vtk",
)
def load_man() -> WidgetDataModel:
    url = "https://vedo.embl.es/examples/data/man.vtk"
    return WidgetDataModel(value=url, type=StandardType.MESH, title="man.vtk")

def main():
    ui = new_window()
    ui.show(run=True)

if __name__ == "__main__":
    main()
