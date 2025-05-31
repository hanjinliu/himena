import time
from qtpy import QtWidgets as QtW, QtCore
from superqt.utils import thread_worker
import numpy as np

from himena import new_window, StandardType
from himena.widgets import SubWindow, MainWindow
from himena.plugins import register_dock_widget_action


# This example shows how to create a simple image acquisition widget for microscopy.
# QImageAcquisitionControl is a plugin dock widget that has a button to start and stop
# image acquisition, and a spinbox to set the laser power. The acquired images are
# generated randomly using Poisson distribution, but practically this would be replaced
# with the actual image acquisition code.

class QImageAcquisitionControl(QtW.QWidget):
    def __init__(self, ui: MainWindow):
        super().__init__()
        self._ui = ui
        self._acquire_btn = QtW.QPushButton("Acquire")
        self._acquire_btn.clicked.connect(self._toggle_acquisition)

        self._laser_power_spinbox = QtW.QSpinBox()
        self._laser_power_spinbox.setRange(0, 100)
        self._laser_power_spinbox.setValue(5)
        self._laser_power_spinbox.setSuffix(" %")

        layout = QtW.QVBoxLayout(self)
        layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
        layout.addWidget(self._acquire_btn)
        layout.addWidget(self._laser_power_spinbox)
        self._window_acquisition: SubWindow | None = None

    def _toggle_acquisition(self):
        if self._is_acquiring():
            self._acquire_btn.setText("Acquire")
        else:
            self._acquire_btn.setText("Stop")
            self._start_worker()

    def _start_worker(self):
        worker = self._acquire_image()
        worker.yielded.connect(self._on_yielded)
        worker.start()

    @thread_worker
    def _acquire_image(self):
        """Generate random images."""
        while self._is_acquiring():
            time.sleep(0.05)
            power = self._laser_power_spinbox.value()
            yield np.random.poisson(lam=power*2, size=(100, 100)).astype(np.uint16)

    def _is_acquiring(self):
        return self._acquire_btn.text() == "Stop"

    def _on_yielded(self, arr: np.ndarray):
        win = self._window_acquisition
        if win is None or not win.is_alive:
            win = self._ui.add_object(arr, type=StandardType.IMAGE, title="Acquisition")
            self._window_acquisition = win
        else:
            win.update_value(arr)

@register_dock_widget_action(
    title="Image Acquisition",
    singleton=True,
    command_id="test-image-acquisition",
)
def install_image_acquisition(ui: MainWindow):
    return QImageAcquisitionControl(ui)

if __name__ == "__main__":
    ui = new_window()
    ui.show_notification(
        "Open the test widget in Tools > Dock widgets > Image Acquisition"
    )
    ui.show(run=True)
