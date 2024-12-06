from __future__ import annotations

from enum import Enum, auto
import numpy as np
from qtpy import QtWidgets as QtW
from qtpy import QtCore

from himena.qt._magicgui._toggle_switch import QLabeledToggleSwitch
from himena.builtins.qt.widgets._image_components import QHistogramView


class ImageType(Enum):
    SINGLE = auto()
    RGB = auto()
    MULTI = auto()


class ComplexMode(Enum):
    REAL = auto()
    IMAG = auto()
    ABS = auto()
    LOG_ABS = auto()
    PHASE = auto()


class QImageViewControl(QtW.QWidget):
    interpolation_changed = QtCore.Signal(bool)
    clim_changed = QtCore.Signal(tuple)
    auto_contrast_requested = QtCore.Signal()
    complex_mode_change_requested = QtCore.Signal(str, str)  # old, new
    channel_mode_change_requested = QtCore.Signal(str)

    def __init__(self):
        super().__init__()
        layout = QtW.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)

        spacer = QtW.QWidget()
        spacer.setSizePolicy(
            QtW.QSizePolicy.Policy.Expanding, QtW.QSizePolicy.Policy.Expanding
        )

        self._complex_mode_combo = QtW.QComboBox()
        self._complex_mode_combo.addItems(["Real", "Imag", "Abs", "Log Abs", "Phase"])
        self._complex_mode_combo.setCurrentIndex(2)
        self._complex_mode_old = "Abs"
        self._complex_mode_combo.currentTextChanged.connect(self._complex_mode_changed)

        self._channel_mode_combo = QtW.QComboBox()
        self._channel_mode_combo.addItems([""])
        self._channel_mode_combo.currentTextChanged.connect(
            self.channel_mode_change_requested.emit
        )
        self._image_type = ImageType.SINGLE

        self._auto_contrast_btn = QtW.QPushButton("Auto")
        self._auto_contrast_btn.clicked.connect(self.auto_contrast_requested.emit)
        self._auto_contrast_btn.setToolTip("Auto contrast")

        self._histogram = QHistogramView()
        self._histogram.setFixedWidth(120)
        self._histogram.clim_changed.connect(self.clim_changed.emit)

        self._interpolation_check_box = QLabeledToggleSwitch()
        self._interpolation_check_box.setText("smooth")
        self._interpolation_check_box.setChecked(False)
        self._interpolation_check_box.setMaximumHeight(36)
        self._interpolation_check_box.toggled.connect(self.interpolation_changed.emit)

        self._hover_info = QtW.QLabel()

        layout.addWidget(spacer)
        layout.addWidget(self._hover_info)
        layout.addWidget(self._complex_mode_combo)
        layout.addWidget(self._channel_mode_combo)
        layout.addWidget(self._auto_contrast_btn)
        layout.addWidget(self._histogram)
        layout.addWidget(self._interpolation_check_box)
        self._complex_mode_combo.hide()
        self._channel_mode_combo.hide()

    def _complex_mode_changed(self):
        cur = self._complex_mode_combo.currentText()
        self.complex_mode_change_requested.emit(self._complex_mode_old, cur)
        self._complex_mode_old = cur

    def update_for_state(self, is_rgb: bool, nchannels: int, is_complex: bool):
        if is_rgb:
            kind = ImageType.RGB
        elif nchannels > 1:
            kind = ImageType.MULTI
        else:
            kind = ImageType.SINGLE
        if kind != self._image_type:
            if kind is ImageType.RGB:
                self._channel_mode_combo.clear()
                self._channel_mode_combo.addItems(["Color", "Gray"])
                self._channel_mode_combo.show()
            elif kind is ImageType.MULTI:
                self._channel_mode_combo.clear()
                self._channel_mode_combo.addItems(["Comp.", "Mono", "Gray"])
                self._channel_mode_combo.show()
            else:
                self._channel_mode_combo.clear()
                self._channel_mode_combo.addItems([""])
                self._channel_mode_combo.hide()
            self._image_type = kind
            self._channel_mode_combo.setCurrentIndex(0)
        self._complex_mode_combo.setVisible(is_complex)
        return None

    def complex_transform(self, arr: np.ndarray) -> np.ndarray:
        """Transform complex array according to the current complex mode."""
        if self._complex_mode_combo.currentText() == "Real":
            return arr.real
        if self._complex_mode_combo.currentText() == "Imag":
            return arr.imag
        if self._complex_mode_combo.currentText() == "Abs":
            return np.abs(arr)
        if self._complex_mode_combo.currentText() == "Log Abs":
            return np.log(np.abs(arr) + 1e-6)
        if self._complex_mode_combo.currentText() == "Phase":
            return np.angle(arr)
        return arr
