from __future__ import annotations

from typing import TYPE_CHECKING
from qtpy import QtWidgets as QtW
from qtpy import QtGui, QtCore
import numpy as np
from cmap import Colormap

from himena.consts import StandardType
from himena.standards import roi, model_meta
from himena.qt._utils import qsignal_blocker
from himena.types import WidgetDataModel
from himena.plugins import protocol_override
from himena._data_wrappers import ArrayWrapper, wrap_array
from himena.builtins.qt.widgets._image_components import (
    QImageGraphicsView,
    QRoi,
    QDimsSlider,
    QRoiButtons,
    QImageViewControl,
)

if TYPE_CHECKING:
    from numpy.typing import NDArray


class QDefaultImageView(QtW.QWidget):
    def __init__(self):
        super().__init__()
        layout = QtW.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self._roi_buttons = QRoiButtons()
        self._roi_buttons.mode_changed.connect(self._on_mode_changed)
        self._image_graphics_view = QImageGraphicsView()
        self._image_graphics_view.hovered.connect(self._on_hovered)
        self._image_graphics_view.mode_changed.connect(self._roi_buttons.set_mode)
        self._dims_slider = QDimsSlider()
        layout.addWidget(self._roi_buttons)
        layout.addWidget(self._image_graphics_view)
        layout.addWidget(self._dims_slider)

        self._image_graphics_view.roi_added.connect(self._on_roi_added)
        self._image_graphics_view.roi_removed.connect(self._on_roi_removed)
        self._dims_slider.valueChanged.connect(self._slider_changed)

        self._roi_list = roi.RoiListModel()
        self._control = QImageViewControl()
        self._control.interpolation_changed.connect(self._interpolation_changed)
        self._control.clim_changed.connect(self._clim_changed)
        self._control.auto_contrast_requested.connect(self._auto_contrast)
        self._arr: ArrayWrapper | None = None
        self._is_modified = False
        self._clim: tuple[float, float] = (0, 255)
        self._colormaps = [Colormap("gray")]
        self._minmax: tuple[float, float] = (0, 255)
        self._current_image_slice = None
        self._is_rgb = False
        self._channel_axis: int | None = None

    @protocol_override
    @classmethod
    def display_name(cls) -> str:
        return "Built-in Image Viewer"

    @protocol_override
    def update_model(self, model: WidgetDataModel):
        arr = wrap_array(model.value)
        is_initialized = self._arr is not None
        is_same_dimensionality = self._arr is not None and arr.ndim == self._arr.ndim
        ndim_rem = arr.ndim - 2
        if arr.shape[-1] in (3, 4) and arr.ndim > 2:
            ndim_rem -= 1
            self._is_rgb = True
        else:
            self._is_rgb = False

        # override widget state if metadata is available
        axes = arr.axis_names()
        check_smoothing = False
        current_indices = None
        self._arr = arr
        if isinstance(meta := model.metadata, model_meta.ImageMeta):
            # TODO: consider other attributes
            if meta.rois:
                self._roi_list = meta.rois
            if meta.interpolation == "linear":
                check_smoothing = True
            if meta.axes:
                axes = meta.axes
            if meta.is_rgb:
                self._is_rgb = True
            if meta.channel_axis is not None:
                self._channel_axis = meta.channel_axis
            if meta.current_indices:
                current_indices = meta.current_indices

        if is_initialized and is_same_dimensionality:
            sl_0 = self._dims_slider.value()
        else:
            sl_0 = (0,) * ndim_rem
        img_slice = arr.get_slice(sl_0)
        if img_slice.dtype.kind == "c":
            img_slice = np.abs(img_slice)  # complex to float

        # guess clim
        self._minmax = _clim = _guess_clim(arr, img_slice)
        if self._is_rgb:
            self._minmax = (0, 255)  # override for RGB images
        elif self._minmax[0] == self._minmax[1]:
            self._minmax = self._minmax[0], self._minmax[0] + 1

        if arr.dtype.kind in "uib":
            self._control._histogram.setValueFormat(".0f")
        else:
            self._control._histogram.setValueFormat(".3g")
        self._clim = _clim

        self._set_image_slice(img_slice, self._clim)
        self._dims_slider._refer_array(arr, axes, is_rgb=self._is_rgb)
        if current_indices is not None:
            self._dims_slider.setValue(current_indices[: self._dims_slider.count()])

        self._control._interpolation_check_box.setChecked(check_smoothing)
        self._image_graphics_view.update()
        return None

    @protocol_override
    def to_model(self) -> WidgetDataModel[NDArray[np.uint8]]:
        assert self._arr is not None

        if self._control._interpolation_check_box.isChecked():
            interp = "linear"
        else:
            interp = "nearest"
        clim = self._clim
        _all = slice(None)
        current_indices = self._dims_slider.value()
        current_slices = current_indices + (_all, _all)
        if item := self._image_graphics_view._current_roi_item:
            current_roi = item.toRoi(current_indices)
        else:
            current_roi = None
        return WidgetDataModel(
            value=self._arr.arr,
            type=self.model_type(),
            extension_default=".png",
            metadata=model_meta.ImageMeta(
                current_indices=current_slices,
                interpolation=interp,
                contrast_limits=clim,
                rois=self._roi_list,
                current_roi=current_roi,
                is_rgb=self._is_rgb,
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
        """Convert any array to one that can be passed to QImage."""
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

    def setFocus(self):
        return self._image_graphics_view.setFocus()

    def leaveEvent(self, ev) -> None:
        self._control._hover_info.setText("")

    def _slider_changed(self, value: tuple[int, ...]):
        # `image_slice` given only when it is available (for performance)
        if self._arr is None:
            return
        img_slice = self._arr.get_slice(value)
        self._set_image_slice(img_slice, self._clim)

    def _set_image_slice(self, img: NDArray[np.number], clim: tuple[float, float]):
        with qsignal_blocker(self._control._histogram):
            self._image_graphics_view.set_array(self.as_image_array(img, clim))
            self._control._histogram.set_hist_for_array(
                img, clim, self._minmax, is_rgb=self._is_rgb
            )
            rois = self._roi_list.get_rois_on_slice(self._dims_slider.value())
            self._image_graphics_view.set_rois(rois)

        self._current_image_slice = img

    def _interpolation_changed(self, checked: bool):
        self._image_graphics_view.setSmoothing(checked)

    def _clim_changed(self, clim: tuple[float, float]):
        self._clim = clim
        with qsignal_blocker(self._control._histogram):
            self._image_graphics_view.set_array(
                self.as_image_array(self._current_image_slice, clim),
                clear_rois=False,
            )

    def _auto_contrast(self):
        if self._arr is None:
            return
        sl = self._dims_slider.value()
        img_slice = self._arr.get_slice(sl)
        min_, max_ = img_slice.min(), img_slice.max()
        self._clim = min_, max_
        self._control._histogram.set_clim(self._clim)
        self._minmax = min(self._minmax[0], min_), max(self._minmax[1], max_)
        self._set_image_slice(img_slice, self._clim)

    def _on_roi_added(self, qroi: QRoi):
        roi = qroi.toRoi(indices=self._dims_slider.value())
        self._roi_list.add_roi(roi)

    def _on_roi_removed(self, idx: int):
        del self._roi_list[idx]

    def _on_mode_changed(self, mode):
        self._image_graphics_view.switch_mode(mode)

    def _on_hovered(self, pos: QtCore.QPointF):
        x, y = pos.x(), pos.y()
        if self._current_image_slice is None:
            return
        iy, ix = int(y), int(x)
        ny, nx, *_ = self._current_image_slice.shape
        if 0 <= iy < ny and 0 <= ix < nx:
            intensity = self._current_image_slice[int(y), int(x)]
            # NOTE: intensity could be an RGBA numpy array.
            if isinstance(intensity, np.ndarray) or self._arr.dtype.kind == "b":
                _int = str(intensity)
            # TODO: complex array support
            else:
                fmt = self._control._histogram._line_low._value_fmt
                _int = format(intensity, fmt)
            self._control._hover_info.setText(f"x={x:.1f}, y={y:.1f}, value={_int}")
        else:
            self._control._hover_info.setText("")

    # forward key events to image graphics view
    def keyPressEvent(self, a0: QtGui.QKeyEvent | None) -> None:
        return self._image_graphics_view.keyPressEvent(a0)

    def keyReleaseEvent(self, a0: QtGui.QKeyEvent | None) -> None:
        return self._image_graphics_view.keyReleaseEvent(a0)


def _guess_clim(
    arr: ArrayWrapper, image_slice: NDArray[np.number]
) -> tuple[float, float]:
    ndim_rem = arr.ndim - 2
    if image_slice.dtype.kind == "b":
        return (0, 1)
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
