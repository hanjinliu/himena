from __future__ import annotations

from typing import TYPE_CHECKING
from qtpy import QtWidgets as QtW
from qtpy import QtGui, QtCore
from superqt import QLabeledSlider, QLabeledDoubleRangeSlider
import numpy as np

from himena.consts import StandardType
from himena.model_meta import ImageMeta
from himena.qt._utils import qsignal_blocker
from himena.types import WidgetDataModel
from himena.plugins import protocol_override
from himena._data_wrappers import ArrayWrapper, wrap_array
from himena.qt._magicgui._toggle_switch import QLabeledToggleSwitch

if TYPE_CHECKING:
    from numpy.typing import NDArray


class _QImageLabel(QtW.QLabel):
    def __init__(self, val):
        super().__init__()
        self._transformation = QtCore.Qt.TransformationMode.SmoothTransformation
        self.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.setSizePolicy(
            QtW.QSizePolicy.Policy.Expanding, QtW.QSizePolicy.Policy.Expanding
        )
        self.set_array(val)

    def set_array(self, val: NDArray[np.uint8]):
        if val.ndim == 2:
            val = np.stack(
                [val] * 3 + [np.full(val.shape, 255, dtype=np.uint8)], axis=2
            )
        else:
            if val.shape[2] == 3:
                val = np.ascontiguousarray(
                    np.concatenate(
                        [val, np.full(val.shape[:2] + (1,), 255, dtype=np.uint8)],
                        axis=2,
                    )
                )
            elif val.shape[2] != 4:
                raise ValueError(
                    "The shape of an RGB image must be (M, N), (M, N, 3) or (M, N, 4), "
                    f"got {val.shape!r}."
                )
        image = QtGui.QImage(
            val, val.shape[1], val.shape[0], QtGui.QImage.Format.Format_RGBA8888
        )
        self._pixmap_orig = QtGui.QPixmap.fromImage(image)
        self._update_pixmap()

    def _update_pixmap(self):
        sz = self.size()
        self.setPixmap(
            self._pixmap_orig.scaled(
                sz,
                QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                self._transformation,
            )
        )

    def resizeEvent(self, ev: QtGui.QResizeEvent) -> None:
        self._update_pixmap()


class QDefaultImageView(QtW.QWidget):
    def __init__(self):
        super().__init__()
        layout = QtW.QVBoxLayout(self)
        self._sliders: list[_QAxisSlider] = []

        self._image_label = _QImageLabel(np.zeros((1, 1), dtype=np.uint8))
        layout.addWidget(self._image_label)

        self._control = QImageViewControl()
        self._control.interpolation_changed.connect(self._interpolation_changed)
        self._control.clim_changed.connect(self._clim_changed)
        self._control.auto_contrast_requested.connect(self._auto_contrast)
        self._arr: ArrayWrapper | None = None
        self._clim: tuple[float, float] = (0, 255)
        self._minmax: tuple[float, float] = (0, 255)

    @protocol_override
    def update_model(self, model: WidgetDataModel):
        arr = wrap_array(model.value)
        ndim_rem = arr.ndim - 2
        if arr.shape[-1] in (3, 4) and ndim_rem > 0:
            ndim_rem -= 1

        sl_0 = (0,) * ndim_rem
        img_slice = arr.get_slice(sl_0)
        if img_slice.dtype.kind == "c":
            img_slice = np.abs(img_slice)  # complex to float

        # guess clim
        self._minmax = self._clim = _guess_clim(arr, img_slice)
        if self._minmax[0] == self._minmax[1]:
            self._minmax = self._minmax[0], self._minmax[0] + 1
        self._control._clim_slider.setMinimum(self._minmax[0])
        self._control._clim_slider.setMaximum(self._minmax[1])
        with qsignal_blocker(self._control._clim_slider):
            self._control._clim_slider.setValue(self._clim)
        self._image_label.set_array(self.as_image_array(img_slice, self._clim))

        nsliders = len(self._sliders)
        if nsliders > ndim_rem:
            for i in range(ndim_rem, nsliders):
                slider = self._sliders.pop()
                self.layout().removeWidget(slider)
                slider.deleteLater()
        elif nsliders < ndim_rem:
            for i in range(nsliders, ndim_rem):
                self._make_slider(arr.shape[i])
        # update axis names
        for aname, slider in zip(arr.axis_names(), self._sliders):
            slider._label.setText(aname)
        self._arr = arr

        self._slider_changed(img_slice=img_slice)
        if img_slice.dtype.kind in "cf":
            self._control._clim_slider.setDecimals(2)
        else:
            self._control._clim_slider.setDecimals(0)

    @protocol_override
    def to_model(self) -> WidgetDataModel[NDArray[np.uint8]]:
        assert self._arr is not None

        if self._control._interpolation_check_box.isChecked():
            interp = "linear"
        else:
            interp = "nearest"
        clim = self._clim
        return WidgetDataModel(
            value=self._arr.arr,
            type=self.model_type(),
            extension_default=".png",
            additional_data=ImageMeta(
                current_indices=[sl._slider.value() for sl in self._sliders],
                interpolation=interp,
                contrast_limits=clim,
            ),
        )

    @protocol_override
    def model_type(self) -> str:
        return StandardType.IMAGE

    @protocol_override
    def size_hint(self) -> tuple[int, int]:
        return 400, 400

    @protocol_override
    def is_editable(self) -> bool:
        return False

    @protocol_override
    def control_widget(self) -> QtW.QWidget:
        return self._control

    def as_image_array(
        self,
        arr: NDArray[np.number],
        clim: tuple[float, float],
    ) -> NDArray[np.uint8]:
        cmin, cmax = clim
        if arr.dtype.kind == "b":
            arr_normed = np.where(arr, np.uint8(255), np.uint8(0))
        elif cmax > cmin:
            arr_normed = (
                ((arr - cmin) / (cmax - cmin) * 255).clip(0, 255).astype(np.uint8)
            )
        else:
            arr_normed = np.zeros(arr.shape, dtype=np.uint8)

        out = np.ascontiguousarray(arr_normed)
        return out

    def _slider_changed(self, *, img_slice=None):
        # `image_slice` given only when it is available (for performance)
        if self._arr is None:
            return
        if img_slice is None:
            img_slice = self._current_image_slice()
        self._image_label.set_array(self.as_image_array(img_slice, self._clim))
        self._control._histogram.set_hist_for_array(img_slice, self._clim, self._minmax)

    def _current_image_slice(self) -> NDArray[np.number]:
        sl = tuple(sl._slider.value() for sl in self._sliders)
        return self._arr.get_slice(sl)

    def _interpolation_changed(self, checked: bool):
        if checked:
            tr = QtCore.Qt.TransformationMode.SmoothTransformation
        else:
            tr = QtCore.Qt.TransformationMode.FastTransformation
        self._image_label._transformation = tr
        self._image_label._update_pixmap()

    def _clim_changed(self, clim: tuple[float, float]):
        self._clim = clim
        self._slider_changed()

    def _auto_contrast(self):
        if self._arr is None:
            return
        img_slice = self._current_image_slice()
        min_, max_ = img_slice.min(), img_slice.max()
        self._clim = min_, max_
        with qsignal_blocker(self._control._clim_slider):
            self._control._clim_slider.setValue(self._clim)
        self._minmax = min(self._minmax[0], min_), max(self._minmax[1], max_)
        self._slider_changed(img_slice=img_slice)

    def _make_slider(self, size: int) -> _QAxisSlider:
        slider = _QAxisSlider()
        self._sliders.append(slider)
        self.layout().addWidget(slider, alignment=QtCore.Qt.AlignmentFlag.AlignBottom)
        slider._slider.setRange(0, size - 1)
        slider._slider.valueChanged.connect(self._slider_changed)
        return slider


class _QAxisSlider(QtW.QWidget):
    def __init__(self) -> None:
        super().__init__()
        layout = QtW.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._label = QtW.QLabel()
        self._label.setFixedWidth(30)
        self._slider = QLabeledSlider(QtCore.Qt.Orientation.Horizontal)

        layout.addWidget(self._label)
        layout.addWidget(self._slider)


class QImageViewControl(QtW.QWidget):
    interpolation_changed = QtCore.Signal(bool)
    clim_changed = QtCore.Signal(tuple)
    auto_contrast_requested = QtCore.Signal()

    def __init__(self):
        super().__init__()
        layout = QtW.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)

        self._histogram = _QHistogram()
        spacer = QtW.QWidget()
        spacer.setSizePolicy(
            QtW.QSizePolicy.Policy.Expanding, QtW.QSizePolicy.Policy.Expanding
        )

        self._auto_contrast_btn = QtW.QPushButton("Auto")
        self._auto_contrast_btn.clicked.connect(self.auto_contrast_requested.emit)
        self._auto_contrast_btn.setToolTip("Auto contrast")
        self._clim_slider = _QContrastRangeSlider()
        self._clim_slider.valueChanged.connect(self.clim_changed.emit)

        self._histogram.setFixedWidth(120)
        self._clim_slider.setFixedWidth(120)

        self._interpolation_check_box = QLabeledToggleSwitch()
        self._interpolation_check_box.setText("smooth")
        self._interpolation_check_box.setChecked(True)
        self._interpolation_check_box.setMaximumHeight(36)
        self._interpolation_check_box.toggled.connect(self.interpolation_changed.emit)

        layout.addWidget(spacer)
        layout.addWidget(self._auto_contrast_btn)
        layout.addWidget(self._clim_slider)
        layout.addWidget(self._histogram)
        layout.addWidget(self._interpolation_check_box)


class _QContrastRangeSlider(QLabeledDoubleRangeSlider):
    def __init__(self):
        super().__init__(QtCore.Qt.Orientation.Horizontal)
        self.setToolTip("Contrast limits")
        self.setEdgeLabelMode(self.EdgeLabelMode.NoLabel)
        self.setHandleLabelPosition(self.LabelPosition.LabelsAbove)
        self.setRange(0, 255)


class _QHistogram(_QImageLabel):
    def __init__(self):
        super().__init__(np.zeros((64, 256), dtype=np.uint8))
        self.setToolTip("Histogram of the image intensity")

    def set_hist_for_array(
        self,
        arr: NDArray[np.number],
        clim: tuple[float, float],
        minmax: tuple[float, float],
    ):
        _min, _max = minmax
        nbin = 128
        h0 = 64
        if _max > _min:
            normed = ((arr - _min) / (_max - _min) * nbin).astype(np.uint8) // 2
            hist = np.bincount(normed.ravel(), minlength=nbin)
            hist = hist / hist.max() * h0
            indices = np.repeat(np.arange(h0)[::-1, None], nbin, axis=1)
            alpha = np.zeros((h0, nbin), dtype=np.uint8)
            alpha[indices < hist[None]] = 255
            colors = np.zeros((h0, nbin, 3), dtype=np.uint8)
            hist_image = np.concatenate([colors, alpha[:, :, None]], axis=2)
            cmin_x = (clim[0] - _min) / (_max - _min) * (nbin - 2) + 1
            cmax_x = (clim[1] - _min) / (_max - _min) * (nbin - 2)
            hist_image[:, int(cmin_x)] = (255, 0, 0, 255)
            hist_image[:, int(cmax_x)] = (255, 0, 0, 255)
        else:
            hist_image = np.zeros((h0, nbin, 4), dtype=np.uint8)
        image = QtGui.QImage(
            hist_image,
            hist_image.shape[1],
            hist_image.shape[0],
            QtGui.QImage.Format.Format_RGBA8888,
        )
        self._pixmap_orig = QtGui.QPixmap.fromImage(image)
        self._update_pixmap()

    def _update_pixmap(self):
        sz = self.size()
        self.setPixmap(
            self._pixmap_orig.scaled(
                sz,
                QtCore.Qt.AspectRatioMode.IgnoreAspectRatio,
                self._transformation,
            )
        )


def _guess_clim(
    arr: ArrayWrapper, image_slice: NDArray[np.number]
) -> tuple[float, float]:
    ndim_rem = arr.ndim - 2
    if image_slice.dtype.kind == "b":
        clim = (0, 1)
    else:
        if ndim_rem == 0:
            clim = (image_slice.min(), image_slice.max())
        else:
            dim3_size = arr.shape[-3]
            if dim3_size == 1:
                clim = (image_slice.min(), image_slice.max())
            elif dim3_size < 4:
                sl_last = (0,) * (ndim_rem - 1) + (dim3_size - 1,)
                image_slice_last = arr.get_slice(sl_last)
                clim = (
                    min(image_slice.min(), image_slice_last.min()),
                    max(image_slice.max(), image_slice_last.max()),
                )
            else:
                sl_last = (0,) * (ndim_rem - 1) + (dim3_size - 1,)
                sl_middle = (0,) * (ndim_rem - 1) + (dim3_size // 2,)
                image_slice_last = arr.get_slice(sl_last)
                image_slice_middle = arr.get_slice(sl_middle)
                clim = (
                    min(
                        image_slice.min(),
                        image_slice_last.min(),
                        image_slice_middle.min(),
                    ),
                    max(
                        image_slice.max(),
                        image_slice_last.max(),
                        image_slice_middle.max(),
                    ),
                )
    return clim
