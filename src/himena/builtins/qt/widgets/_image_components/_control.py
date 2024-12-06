from __future__ import annotations

from qtpy import QtWidgets as QtW
from qtpy import QtCore

from himena.qt._magicgui._toggle_switch import QLabeledToggleSwitch
from himena.builtins.qt.widgets._image_components import QHistogramView


class QImageViewControl(QtW.QWidget):
    interpolation_changed = QtCore.Signal(bool)
    clim_changed = QtCore.Signal(tuple)
    auto_contrast_requested = QtCore.Signal()
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

        self._channel_mode_combo = QtW.QComboBox()
        self._channel_mode_combo.addItems(["Comp.", "Mono", "Gray"])
        self._channel_mode_combo.currentTextChanged.connect(
            self.channel_mode_change_requested.emit
        )
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
        layout.addWidget(self._channel_mode_combo)
        layout.addWidget(self._auto_contrast_btn)
        layout.addWidget(self._histogram)
        layout.addWidget(self._interpolation_check_box)

    def update_for_state(self, is_rgb: bool, nchannels: int):
        if is_rgb:
            self._channel_mode_combo.clear()
            self._channel_mode_combo.addItems(["Color", "Gray"])
            self._channel_mode_combo.show()
        elif nchannels > 1:
            self._channel_mode_combo.clear()
            self._channel_mode_combo.addItems(["Comp.", "Mono", "Gray"])
            self._channel_mode_combo.show()
        else:
            self._channel_mode_combo.hide()
