from __future__ import annotations

from typing import TYPE_CHECKING
from enum import Enum, auto
import numpy as np
from qtpy import QtWidgets as QtW
from qtpy import QtCore

from himena.qt._magicgui._toggle_switch import QLabeledToggleSwitch
from himena.builtins.qt.widgets._image_components import QHistogramView
from himena.qt._utils import qsignal_blocker

if TYPE_CHECKING:
    from himena.builtins.qt.widgets.image import QImageView


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
    def __init__(self, image_view: QImageView):
        super().__init__()
        self._image_view = image_view
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
        self._complex_mode_combo.setToolTip("Method to display complex data")
        self._complex_mode_old = "Abs"
        self._complex_mode_combo.currentTextChanged.connect(
            self._on_complex_mode_change
        )

        self._channel_mode_combo = QtW.QComboBox()
        self._channel_mode_combo.addItems([""])
        self._channel_mode_combo.currentTextChanged.connect(
            self._on_channel_mode_change
        )
        self._channel_mode_combo.setToolTip("Method to display multi-channel data")
        self._image_type = ImageType.SINGLE

        self._auto_contrast_btn = QtW.QPushButton("Auto")
        self._auto_contrast_btn.clicked.connect(self._auto_contrast)
        self._auto_contrast_btn.setToolTip("Auto contrast")

        self._histogram = QHistogramView()
        self._histogram.setFixedWidth(120)
        self._histogram.clim_changed.connect(self._clim_changed)

        self._interp_check_box = QLabeledToggleSwitch()
        self._interp_check_box.setText("smooth")
        self._interp_check_box.setChecked(False)
        self._interp_check_box.setMaximumHeight(36)
        self._interp_check_box.toggled.connect(self._interpolation_changed)

        self._hover_info = QtW.QLabel()

        layout.addWidget(spacer)
        layout.addWidget(self._hover_info)
        layout.addWidget(self._complex_mode_combo)
        layout.addWidget(self._channel_mode_combo)
        layout.addWidget(self._auto_contrast_btn)
        layout.addWidget(self._histogram)
        layout.addWidget(self._interp_check_box)
        self._complex_mode_combo.hide()
        self._channel_mode_combo.hide()

    def update_for_state(
        self,
        is_rgb: bool,
        nchannels: int,
        dtype,
    ):
        dtype = np.dtype(dtype)
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
        self._complex_mode_combo.setVisible(dtype.kind == "c")
        if dtype.kind in "uib":
            self._histogram.setValueFormat(".0f")
        else:
            self._histogram.setValueFormat(".3g")
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

    def _interpolation_changed(self, checked: bool):
        self._image_view._img_view.setSmoothing(checked)

    def _clim_changed(self, clim: tuple[float, float]):
        view = self._image_view
        ch = view.current_channel()
        ch.clim = clim
        idx = ch.channel_index or 0
        with qsignal_blocker(self._histogram):
            view._img_view.set_array(
                idx,
                ch.transform_image(
                    view._current_image_slices[idx],
                    complex_transform=self.complex_transform,
                    is_rgb=view._is_rgb,
                    is_gray=view._composite_state() == "Gray",
                ),
            )

    def _on_channel_mode_change(self, mode: str):
        self._image_view._reset_image()

    def _on_complex_mode_change(self):
        cur = self._complex_mode_combo.currentText()
        self._image_view._reset_image()
        self._complex_mode_old = cur
        # TODO: auto contrast and update colormap

    def _auto_contrast(self):
        view = self._image_view
        if view._arr is None:
            return
        sl = view._dims_slider.value()
        img_slice = view._get_image_slice_for_channel(sl)
        if img_slice.dtype.kind == "c":
            img_slice = self.complex_transform(img_slice)
        min_, max_ = img_slice.min(), img_slice.max()
        ch = view.current_channel(sl)
        ch.clim = (min_, max_)
        ch.minmax = min(ch.minmax[0], min_), max(ch.minmax[1], max_)
        self._histogram.set_clim((min_, max_))
        view._set_image_slice(img_slice, ch)
