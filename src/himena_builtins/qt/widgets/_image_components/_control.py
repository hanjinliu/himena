from __future__ import annotations

from typing import TYPE_CHECKING
import numpy as np
from qtpy import QtWidgets as QtW
from qtpy import QtCore, QtGui
from superqt.utils import qthrottled

from himena.qt._magicgui._toggle_switch import QLabeledToggleSwitch
from himena_builtins.qt.widgets._image_components import QHistogramView
from himena.qt._utils import qsignal_blocker
from himena._enum import StrEnum

if TYPE_CHECKING:
    from himena_builtins.qt.widgets.image import QImageView, ChannelInfo


class ImageType(StrEnum):
    SINGLE = "Single"
    RGB = "RGB"
    MULTI = "Multi"
    OTHERS = "Others"


class ComplexMode(StrEnum):
    REAL = "Real"
    IMAG = "Imag"
    ABS = "Abs"
    LOG_ABS = "Log Abs"
    PHASE = "Phase"


class ChannelMode(StrEnum):
    COMP = "Comp."
    MONO = "Mono"
    GRAY = "Gray"


class RGBMode(StrEnum):
    COLOR = "Color"
    GRAY = "Gray"


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
        self._complex_mode_combo.addItems(
            [ComplexMode.REAL, ComplexMode.IMAG, ComplexMode.ABS, ComplexMode.LOG_ABS,
             ComplexMode.PHASE]
        )  # fmt: skip
        self._complex_mode_combo.setCurrentIndex(2)
        self._complex_mode_combo.setToolTip("Method to display complex data")
        self._complex_mode_old = "Abs"
        self._complex_mode_combo.currentTextChanged.connect(
            self._on_complex_mode_change
        )

        self._channel_visibilities = QChannelToggleSwitches()
        self._channel_visibilities.stateChanged.connect(
            self._on_channel_visibility_change
        )

        self._channel_mode_combo = QtW.QComboBox()
        self._channel_mode_combo.addItems([""])
        self._channel_mode_combo.currentTextChanged.connect(
            self._on_channel_mode_change
        )
        self._channel_mode_combo.setToolTip("Method to display multi-channel data")
        self._image_type = ImageType.OTHERS

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
        layout.addWidget(self._channel_visibilities)
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
                self._channel_mode_combo.addItems([RGBMode.COLOR, RGBMode.GRAY])
                self._channel_mode_combo.show()
                self._channel_visibilities.hide()
            elif kind is ImageType.MULTI:
                self._channel_mode_combo.clear()
                self._channel_mode_combo.addItems(
                    [ChannelMode.COMP, ChannelMode.MONO, ChannelMode.GRAY]
                )
                self._channel_mode_combo.show()
                self._channel_visibilities.show()
            else:
                self._channel_mode_combo.clear()
                self._channel_mode_combo.addItems([""])
                self._channel_mode_combo.hide()
                self._channel_visibilities.hide()
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
        if self._complex_mode_combo.currentText() == ComplexMode.REAL:
            return arr.real
        if self._complex_mode_combo.currentText() == ComplexMode.IMAG:
            return arr.imag
        if self._complex_mode_combo.currentText() == ComplexMode.ABS:
            return np.abs(arr)
        if self._complex_mode_combo.currentText() == ComplexMode.LOG_ABS:
            return np.log(np.abs(arr) + 1e-6)
        if self._complex_mode_combo.currentText() == ComplexMode.PHASE:
            return np.angle(arr)
        return arr

    def _interpolation_changed(self, checked: bool):
        self._image_view._img_view.setSmoothing(checked)

    @qthrottled(timeout=100)
    def _clim_changed(self, clim: tuple[float, float]):
        view = self._image_view
        ch = view.current_channel()
        ch.clim = clim
        idx = ch.channel_index or 0
        imtup = view._current_image_slices[idx]
        with qsignal_blocker(self._histogram):
            _grays = (RGBMode.GRAY, ChannelMode.GRAY)
            if imtup.visible:
                arr = ch.transform_image(
                    view._current_image_slices[idx].arr,
                    complex_transform=self.complex_transform,
                    is_rgb=view._is_rgb,
                    is_gray=self._channel_mode_combo.currentText() in _grays,
                )
            else:
                arr = None
            view._img_view.set_array(idx, arr)

    def _on_channel_mode_change(self, mode: str):
        self._channel_visibilities.setVisible(mode == ChannelMode.COMP)
        self._on_channel_visibility_change()

    def _channel_visibility(self) -> list[bool]:
        caxis = self._image_view._channel_axis
        if caxis is None:
            return [True]  # No channels, always visible
        is_composite = self._channel_mode_combo.currentText() == ChannelMode.COMP
        if is_composite:
            visibilities = self._channel_visibilities._check_states()
        else:
            visibilities = [False] * len(self._channel_visibilities._toggle_switches)
            sl = self._image_view._dims_slider.value()
            ith_channel = sl[caxis]
            if len(visibilities) <= ith_channel:
                return [True] * len(sl)  # before initialization
            visibilities[ith_channel] = True
        return visibilities

    def _on_channel_visibility_change(self):
        visibilities = self._channel_visibility()
        self._image_view._update_image_visibility(visibilities)

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


class QChannelToggleSwitches(QtW.QScrollArea):
    stateChanged = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(150)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        central = QtW.QWidget()
        layout = QtW.QGridLayout(central)
        layout.setContentsMargins(2, 2, 2, 2)
        self._layout = layout
        self._toggle_switches: list[QLabeledToggleSwitch] = []
        self.setWidget(central)
        self._label_font = QtGui.QFont("Arial", 8)

    def set_channels(self, channels: list[ChannelInfo]):
        labels = [ch.name for ch in channels]
        for ith in range(len(self._toggle_switches), len(labels)):
            sw = QLabeledToggleSwitch()
            sw.setSize(9)
            sw.setChecked(True)
            sw.setFont(self._label_font)
            sw.toggled.connect(self._emit_state_changed)
            row, col = divmod(ith, 2)
            self._layout.addWidget(sw, row, col)
            self._toggle_switches.append(sw)
        while len(self._toggle_switches) > len(labels):
            sw = self._toggle_switches.pop()
            sw.setParent(None)
        for i, label in enumerate(labels):
            sw = self._toggle_switches[i]
            sw.setText(label)
            sw._switch._on_color_override = QtGui.QColor.fromRgbF(
                *channels[i].colormap(0.5)
            )

    def _emit_state_changed(self):
        self.stateChanged.emit()

    def _check_states(self) -> list[bool]:
        return [sw.isChecked() for sw in self._toggle_switches]
