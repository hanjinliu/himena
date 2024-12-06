from __future__ import annotations

from itertools import cycle
from typing import TYPE_CHECKING
import warnings
from qtpy import QtWidgets as QtW
from qtpy import QtGui, QtCore
import numpy as np
from cmap import Colormap
from pydantic_compat import BaseModel, Field, field_validator

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
    """The default nD image viewer widget for himena."""

    def __init__(self):
        super().__init__()
        layout = QtW.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self._roi_buttons = QRoiButtons()
        self._roi_buttons.mode_changed.connect(self._on_roi_mode_changed)
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
        self._control.channel_mode_change_requested.connect(
            self._on_channel_mode_change
        )
        self._arr: ArrayWrapper | None = None
        self._is_modified = False
        self._current_image_slices = None
        self._is_rgb = False
        self._channel_axis: int | None = None
        self._channels = [ChannelInfo()]

    @protocol_override
    @classmethod
    def display_name(cls) -> str:
        return "Built-in Image Viewer"

    @protocol_override
    def update_model(self, model: WidgetDataModel):
        arr = wrap_array(model.value)
        # TODO: if model.value is self._arr.arr, do not execute heavy operations
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

        if self._is_rgb:
            if self._channel_axis not in (-1, arr.ndim - 1, None):
                warnings.warn(
                    "RGB image detected but channel axis is explicitly set to the axis "
                    f"{self._channel_axis}. Ignoring the channel axis setting."
                )
            self._channel_axis = None
        if is_initialized and is_same_dimensionality:
            sl_0 = self._dims_slider.value()
        else:
            sl_0 = (0,) * ndim_rem

        # update sliders
        self._dims_slider._refer_array(arr, axes, is_rgb=self._is_rgb)
        if current_indices is not None:
            self._dims_slider.setValue(current_indices[: self._dims_slider.count()])

        # update channel info
        if self._channel_axis is None:
            nchannels = 1
        else:
            nchannels = arr.shape[self._channel_axis]
        if len(self._channels) != nchannels:
            self._image_graphics_view.set_n_images(nchannels)
            self._channels = prep_channel_infos(nchannels)
        for ch in self._channels:
            if self._is_rgb:
                ch.clim = (0, 255)
                ch.minmax = (0, 255)
            else:
                ch.guess_clim(arr, self._channel_axis)

        if arr.dtype.kind in "uib":
            self._control._histogram.setValueFormat(".0f")
        else:
            self._control._histogram.setValueFormat(".3g")

        img_slices = self._get_image_slices(sl_0)
        self._set_image_slices(img_slices)

        self._control._interpolation_check_box.setChecked(check_smoothing)
        self._control.update_for_state(is_rgb=self._is_rgb, nchannels=nchannels)
        self._image_graphics_view.update()
        return None

    @protocol_override
    def to_model(self) -> WidgetDataModel[NDArray[np.uint8]]:
        assert self._arr is not None

        if self._control._interpolation_check_box.isChecked():
            interp = "linear"
        else:
            interp = "nearest"
        clim = [ch.clim for ch in self._channels]
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

    def setFocus(self):
        return self._image_graphics_view.setFocus()

    def leaveEvent(self, ev) -> None:
        self._control._hover_info.setText("")

    def _composite_state(self) -> str:
        if not self._control._channel_mode_combo.isVisible():
            return "Mono"
        return self._control._channel_mode_combo.currentText()

    def _get_image_slices(
        self, value: tuple[int, ...]
    ) -> list[NDArray[np.number] | None]:
        """Get numpy arrays for each channel (None mean hide the channel)."""
        if self._channel_axis is None:
            return [self._get_image_slice_for_channel(value)]

        if len(self._channels) == 1 or self._composite_state() != "Comp.":
            img_slices = [None] * len(self._channels)
            idx = value[self._channel_axis]
            img_slices[idx] = self._get_image_slice_for_channel(value)
        else:
            img_slices = []
            for i in range(len(self._channels)):
                sl = list(value)
                sl[self._channel_axis] = i
                img_slices.append(self._get_image_slice_for_channel(sl))
        return img_slices

    def _get_image_slice_for_channel(
        self, value: tuple[int, ...]
    ) -> NDArray[np.number]:
        """Get numpy array for current channel."""
        return self._arr.get_slice(tuple(value))

    def _slider_changed(self, value: tuple[int, ...]):
        # `image_slice` given only when it is available (for performance)
        if self._arr is None:
            return
        img_slices = self._get_image_slices(value)
        self._set_image_slices(img_slices)
        rois = self._roi_list.get_rois_on_slice(value)
        self._image_graphics_view.set_rois(rois)

    def _set_image_slice(self, img: NDArray[np.number] | None, channel: ChannelInfo):
        idx = channel.channel_index or 0
        if self._composite_state() == "Gray":
            channel = channel.as_gray()
        alphas = self.prep_alphas(self._current_image_slices)
        with qsignal_blocker(self._control._histogram):
            self._image_graphics_view.set_array(
                idx, channel.transform_image(img, alphas[idx])
            )
            self._control._histogram.set_hist_for_array(
                img, channel.clim, channel.minmax, is_rgb=self._is_rgb
            )
            # draw rois
        self._current_image_slices[idx] = img

    def _set_image_slices(
        self,
        imgs: list[NDArray[np.number] | None],
    ):
        """Set image slices using the channel information.

        This method is only used for updating the entire image slices.
        """
        alphas = self.prep_alphas(imgs)
        with qsignal_blocker(self._control._histogram):
            for i, (img, ch) in enumerate(zip(imgs, self._channels)):
                if self._composite_state() == "Gray":
                    ch = ch.as_gray()
                self._image_graphics_view.set_array(
                    i, ch.transform_image(img, alphas[i])
                )
            ch_cur = self.current_channel()
            idx = ch_cur.channel_index or 0
            self._control._histogram.set_hist_for_array(
                imgs[idx], ch_cur.clim, ch_cur.minmax, is_rgb=self._is_rgb
            )
            rois = self._roi_list.get_rois_on_slice(self._dims_slider.value())
            self._image_graphics_view.set_rois(rois)

        self._current_image_slices = imgs

    def _interpolation_changed(self, checked: bool):
        self._image_graphics_view.setSmoothing(checked)

    def _clim_changed(self, clim: tuple[float, float]):
        ch = self.current_channel()
        ch.clim = clim
        idx = ch.channel_index or 0
        if self._composite_state() == "Gray":
            ch = ch.as_gray()
        alphas = self.prep_alphas(self._current_image_slices)
        with qsignal_blocker(self._control._histogram):
            self._image_graphics_view.set_array(
                idx,
                ch.transform_image(self._current_image_slices[idx], alphas[idx]),
                clear_rois=False,
            )

    def current_channel(self, slider_value: tuple[int] | None = None) -> ChannelInfo:
        if slider_value is None:
            _slider_value = self._dims_slider.value()
        else:
            _slider_value = slider_value
        if self._channel_axis is not None:
            ith = _slider_value[self._channel_axis]
            ch = self._channels[ith]
        else:
            ch = self._channels[0]
        return ch

    def _auto_contrast(self):
        if self._arr is None:
            return
        sl = self._dims_slider.value()
        img_slice = self._get_image_slice_for_channel(sl)
        min_, max_ = img_slice.min(), img_slice.max()
        clim = min_, max_
        ch = self.current_channel(sl)
        ch.clim = clim
        ch.minmax = min(ch.minmax[0], min_), max(ch.minmax[1], max_)
        self._control._histogram.set_clim(clim)
        self._set_image_slice(img_slice, ch)

    def _on_roi_added(self, qroi: QRoi):
        roi = qroi.toRoi(indices=self._dims_slider.value())
        self._roi_list.add_roi(roi)

    def _on_roi_removed(self, idx: int):
        del self._roi_list[idx]

    def _on_roi_mode_changed(self, mode):
        self._image_graphics_view.switch_mode(mode)

    def _on_channel_mode_change(self, mode: str):
        imgs = self._get_image_slices(self._dims_slider.value())
        self._set_image_slices(imgs)

    def _on_hovered(self, pos: QtCore.QPointF):
        x, y = pos.x(), pos.y()
        if self._current_image_slices is None:
            return
        iy, ix = int(y), int(x)
        idx = self.current_channel().channel_index or 0
        cur_img = self._current_image_slices[idx]
        ny, nx, *_ = cur_img.shape
        if 0 <= iy < ny and 0 <= ix < nx:
            intensity = cur_img[int(y), int(x)]
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

    def prep_alphas(self, imgs: list[NDArray[np.number] | None]) -> list[int]:
        alphas = [255] * len(self._channels)
        if self._composite_state() == "Comp.":
            first_img_idx = None
            for i in range(len(imgs)):
                if imgs[i] is not None:
                    first_img_idx = i
                    break
            alphas = [128] * len(imgs)
            if first_img_idx is not None:
                alphas[first_img_idx] = 255
        return alphas


class ChannelInfo(BaseModel):
    clim: tuple[float, float] = Field((0, 255))
    minmax: tuple[float, float] = Field((0, 255))
    colormap: Colormap = Field(default_factory=lambda: Colormap("gray"))
    channel_index: int | None = Field(None)
    label: str | None = Field(None)

    def guess_clim(self, arr: ArrayWrapper, channel_axis: int | None = None):
        if arr.dtype.kind == "b":
            return (0, 1)
        ndim = arr.ndim
        sl = [slice(None)] * ndim
        if self.channel_index is not None:
            sl[channel_axis] = self.channel_index
            if channel_axis < ndim - 3:  # such as (C, T, Z, Y, X), (C, Z, Y, X)
                dim3 = -3
            else:  # such as (T, Z, C, Y, X)
                dim3 = -4
        else:
            dim3 = -2
        slices: list[tuple[int | slice, ...]] = []
        if -dim3 > ndim:
            slices.append(tuple(sl))
        else:
            dim3_size = arr.shape[dim3]
            if dim3_size < 4:
                dim3_indices = [0, -1]
            else:
                dim3_indices = [0, dim3_size // 2, -1]
            for i in dim3_indices:
                sl[dim3] = i
                slices.append(tuple(sl))
        img_slices = [arr.get_slice(sl) for sl in slices]
        clim_min = min(img_slice.min() for img_slice in img_slices)
        clim_max = max(img_slice.max() for img_slice in img_slices)
        self.clim = clim_min, clim_max
        self.minmax = min(self.minmax[0], clim_min), max(self.minmax[1], clim_max)
        return None

    @field_validator("minmax")
    def _validate_minmax(cls, v, values):
        vmin, vmax = v
        if vmin > vmax:
            raise ValueError("minmax[0] must be less than or equal to minmax[1]")
        elif vmin == vmax:
            vmax = vmin + 1
        return vmin, vmax

    def transform_image(
        self,
        arr: NDArray[np.number] | None,
        alpha: int = 255,
    ) -> NDArray[np.uint8] | None:
        if arr is None:
            return None
        cmin, cmax = self.clim
        if arr.dtype.kind == "b":
            false_color = np.array(self.colormap(0, bytes=True))
            true_color = np.array(self.colormap(1, bytes=True))
            arr_normed = np.where(arr[..., np.newaxis], true_color, false_color)
        elif cmax > cmin:
            arr_normed = self.colormap((arr - cmin) / (cmax - cmin), bytes=True)
        else:
            color = np.array(self.colormap(0.5, bytes=True))
            arr_normed = np.broadcast_to(color, arr.shape + (3,))
        if alpha < 255:
            arr_normed[:, :, -1] = alpha
        out = np.ascontiguousarray(arr_normed)
        assert out.dtype == np.uint8
        return out

    def as_gray(self) -> ChannelInfo:
        return self.model_copy(update={"colormap": Colormap("gray")})


def prep_channel_infos(num: int) -> list[ChannelInfo]:
    if num == 1:
        return [ChannelInfo()]
    elif num == 2:
        colors = ["#00FF00", "#FF00FF"]
    elif num == 3:
        colors = ["#00FFFF", "#00FF00", "#FF00FF"]
    elif num == 4:
        colors = ["#00FFFF", "#00FF00", "#FF00FF", "#FF0000"]
    else:
        colors = list(cycle(["#00FFFF", "#00FF00", "#FF00FF", "#FF0000"]))
    return [
        ChannelInfo(colormap=Colormap(["#000000", color]), channel_index=idx)
        for idx, color in enumerate(colors)
    ]
