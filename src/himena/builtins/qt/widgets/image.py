from __future__ import annotations

from itertools import cycle
from typing import TYPE_CHECKING, Callable
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
from himena.widgets import set_status_tip
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
    from himena.builtins.qt.widgets._image_components._graphics_view import Mode


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
        self._control.complex_mode_change_requested.connect(
            self._on_complex_mode_change
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
            _is_rgb = True
        else:
            _is_rgb = False

        # override widget state if metadata is available
        meta_default = model_meta.ImageMeta(
            axes=arr.axis_names(),
            interpolation="linear" if _is_rgb else "nearest",
            is_rgb=_is_rgb,
        )
        self._arr = arr
        if isinstance(meta := model.metadata, model_meta.ImageMeta):
            # TODO: consider other attributes
            if meta.rois:
                meta_default.rois = meta.rois
            if meta.interpolation:
                meta_default.interpolation = meta.interpolation
            if meta.axes:
                meta_default.axes = meta.axes
            if meta.is_rgb:
                meta_default.is_rgb = meta.is_rgb
            if meta.channel_axis is not None:
                meta_default.channel_axis = meta.channel_axis
            if meta.current_indices:
                meta_default.current_indices = meta.current_indices
            if meta.channels:
                meta_default.channels = meta.channels

        self._is_rgb = meta_default.is_rgb
        if meta_default.current_indices is not None:
            sl_0 = meta_default.current_indices[:ndim_rem]
        elif is_initialized and is_same_dimensionality:
            sl_0 = self._dims_slider.value()
        else:
            if meta_default.axes:
                axis_names = [axis.name for axis in meta_default.axes][:ndim_rem]
                print(axis_names)
                sl_0 = tuple(
                    size // 2 if aname.lower() == "z" else 0
                    for aname, size in zip(axis_names, arr.shape)
                )
            else:
                sl_0 = (0,) * ndim_rem
        # update sliders
        self._dims_slider._refer_array(arr, meta_default.axes, is_rgb=self._is_rgb)
        self._dims_slider.setValue(sl_0)

        # update channel info
        if meta_default.channel_axis is None:
            nchannels = 1
        else:
            nchannels = arr.shape[meta_default.channel_axis]

        if len(self._channels) != nchannels:
            self._image_graphics_view.set_n_images(nchannels)
        if len(meta_default.channels) != nchannels:
            self._channels = prep_channel_infos(nchannels)
        else:
            self._channels = [
                ChannelInfo.from_channel(i, c)
                for i, c in enumerate(meta_default.channels)
            ]
        if _is_rgb:
            self._channel_axis = None  # override channel axis for RGB images
        else:
            self._channel_axis = meta_default.channel_axis

        for ch in self._channels:
            if self._is_rgb:
                ch.clim = (0, 255)
                ch.minmax = (0, 255)
            else:
                ch.guess_clim(arr, self._channel_axis)

        self._control.update_for_state(
            is_rgb=self._is_rgb,
            nchannels=nchannels,
            dtype=arr.dtype,
        )

        img_slices = self._get_image_slices(sl_0)
        self._set_image_slices(img_slices)

        self._control._interpolation_check_box.setChecked(
            meta_default.interpolation == "linear"
        )
        return None

    @protocol_override
    def to_model(self) -> WidgetDataModel:
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

    def _set_image_slice(self, img: NDArray[np.number], channel: ChannelInfo):
        idx = channel.channel_index or 0
        alphas = self.prep_alphas()
        with qsignal_blocker(self._control._histogram):
            self._image_graphics_view.set_array(
                idx,
                channel.transform_image(
                    img,
                    alpha=alphas[idx],
                    complex_transform=self._control.complex_transform,
                    is_rgb=self._is_rgb,
                    is_gray=self._composite_state() == "Gray",
                ),
            )
            channel.minmax = (
                min(img.min(), channel.minmax[0]),
                max(img.max(), channel.minmax[1]),
            )
            self._control._histogram.set_hist_for_array(
                img,
                channel.clim,
                channel.minmax,
                is_rgb=self._is_rgb,
                color=color_for_colormap(channel.colormap),
            )
        self._current_image_slices[idx] = img

    def _set_image_slices(
        self,
        imgs: list[NDArray[np.number] | None],
    ):
        """Set image slices using the channel information.

        This method is only used for updating the entire image slices.
        """
        self._current_image_slices = imgs
        alphas = self.prep_alphas()
        with qsignal_blocker(self._control._histogram):
            for i, (img, ch) in enumerate(zip(imgs, self._channels)):
                self._image_graphics_view.set_array(
                    i,
                    ch.transform_image(
                        img,
                        alpha=alphas[i],
                        complex_transform=self._control.complex_transform,
                        is_rgb=self._is_rgb,
                        is_gray=self._composite_state() == "Gray",
                    ),
                )
            ch_cur = self.current_channel()
            idx = ch_cur.channel_index or 0
            self._control._histogram.set_hist_for_array(
                imgs[idx],
                ch_cur.clim,
                ch_cur.minmax,
                is_rgb=self._is_rgb,
                color=color_for_colormap(ch_cur.colormap),
            )
            rois = self._roi_list.get_rois_on_slice(self._dims_slider.value())
            self._image_graphics_view.set_rois(rois)

    def _interpolation_changed(self, checked: bool):
        self._image_graphics_view.setSmoothing(checked)

    def _clim_changed(self, clim: tuple[float, float]):
        ch = self.current_channel()
        ch.clim = clim
        idx = ch.channel_index or 0
        alphas = self.prep_alphas()
        with qsignal_blocker(self._control._histogram):
            self._image_graphics_view.set_array(
                idx,
                ch.transform_image(
                    self._current_image_slices[idx],
                    alpha=alphas[idx],
                    complex_transform=self._control.complex_transform,
                    is_rgb=self._is_rgb,
                    is_gray=self._composite_state() == "Gray",
                ),
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
        if img_slice.dtype.kind == "c":
            img_slice = self._control.complex_transform(img_slice)
        min_, max_ = img_slice.min(), img_slice.max()
        ch = self.current_channel(sl)
        ch.clim = (min_, max_)
        ch.minmax = min(ch.minmax[0], min_), max(ch.minmax[1], max_)
        self._control._histogram.set_clim((min_, max_))
        self._set_image_slice(img_slice, ch)

    def _on_roi_added(self, qroi: QRoi):
        roi = qroi.toRoi(indices=self._dims_slider.value())
        self._roi_list.add_roi(roi)

    def _on_roi_removed(self, idx: int):
        del self._roi_list[idx]

    def _on_roi_mode_changed(self, mode: Mode):
        self._image_graphics_view.switch_mode(mode)
        mode_name = mode.name.replace("_", " ")
        if mode_name.startswith("ROI "):
            mode_name = mode_name[4:]
        set_status_tip(f"Switched to {mode_name} mode.")

    def _reset_image(self):
        imgs = self._get_image_slices(self._dims_slider.value())
        self._set_image_slices(imgs)

    def _on_channel_mode_change(self, mode: str):
        self._reset_image()

    def _on_complex_mode_change(self, old: str, new: str):
        self._reset_image()
        # TODO: auto contrast and update colormap

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

    def prep_alphas(self) -> list[int]:
        imgs = self._current_image_slices
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
    name: str | None = Field(None)
    clim: tuple[float, float] = Field((0.0, 1.0))
    minmax: tuple[float, float] = Field((0.0, 1.0))
    colormap: Colormap = Field(default_factory=lambda: Colormap("gray"))
    channel_index: int | None = Field(None)

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
        if arr.dtype.kind == "c":
            img_slices = [np.abs(img_slice) for img_slice in img_slices]
        clim_min = min(img_slice.min() for img_slice in img_slices)
        clim_max = max(img_slice.max() for img_slice in img_slices)
        self.clim = clim_min, clim_max
        self.minmax = self.clim
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
        complex_transform: Callable[
            [NDArray[np.complexfloating]], NDArray[np.number]
        ] = np.abs,
        is_rgb: bool = False,
        is_gray: bool = False,
    ) -> NDArray[np.uint8] | None:
        """Convenience method to transform the array to a displayable RGBA image."""
        if is_rgb:
            return self.transform_image_rgb(arr, is_gray=is_gray)
        else:
            if is_gray:
                return self.as_gray().transform_image(arr, alpha, complex_transform)
            return self.transform_image_2d(arr, alpha, complex_transform)

    def transform_image_2d(
        self,
        arr: NDArray[np.number] | None,
        alpha: int = 255,
        complex_transform: Callable[
            [NDArray[np.complexfloating]], NDArray[np.number]
        ] = np.abs,
    ) -> NDArray[np.uint8] | None:
        """Transform the array to a displayable RGBA image."""
        if arr is None:
            return None
        if arr.ndim == 3:
            return arr  # RGB
        cmin, cmax = self.clim
        if arr.dtype.kind == "c":
            arr = complex_transform(arr)
        if arr.dtype.kind == "b":
            false_color = np.array(self.colormap(0, bytes=True))
            true_color = np.array(self.colormap(1, bytes=True))
            arr_normed = np.where(arr[..., np.newaxis], true_color, false_color)
        elif cmax > cmin:
            arr_normed = self.colormap((arr - cmin) / (cmax - cmin), bytes=True)
        else:
            color = (np.array(self.colormap(0.5)) * 255).astype(np.uint8)
            arr_normed = np.empty(arr.shape + (4,), dtype=np.uint8)
            arr_normed[:] = color[np.newaxis, np.newaxis]
        if alpha < 255:
            arr_normed[:, :, -1] = alpha
        out = np.ascontiguousarray(arr_normed)
        assert out.dtype == np.uint8
        return out

    def transform_image_rgb(
        self,
        arr: NDArray[np.number] | None,
        is_gray: bool = False,
    ):
        """Transform the RGBA array to a displayable RGBA image."""
        if arr is None:
            return None
        cmin, cmax = self.clim
        amp = 255 / (cmax - cmin)
        if is_gray:
            # make a gray image
            arr_gray = arr[..., 0] * 0.3 + arr[..., 1] * 0.59 + arr[..., 2] * 0.11
            arr_gray = arr_gray.astype(np.uint8)
            if arr.shape[2] == 4:
                alpha = arr[..., 3]
            else:
                alpha = np.full(arr_gray.shape, 255, dtype=np.uint8)
            arr = np.stack([arr_gray, arr_gray, arr_gray, alpha], axis=-1)
        if (cmin, cmax) == (0, 255):
            arr_normed = arr
        else:
            if arr.shape[2] == 3:
                arr_normed = ((arr - cmin) * amp).clip(0, 255).astype(np.uint8)
            else:
                arr_normed = arr.copy()
                if is_gray:
                    sl = slice(None)
                else:
                    sl = (slice(None), slice(None), slice(None, 3))
                arr_normed[sl] = ((arr[sl] - cmin) * amp).clip(0, 255).astype(np.uint8)
        return arr_normed

    def as_gray(self) -> ChannelInfo:
        return self.model_copy(update={"colormap": Colormap("gray")})

    @classmethod
    def from_channel(cls, idx: int, channel: model_meta.ImageChannel) -> ChannelInfo:
        return cls(
            name=channel.name,
            channel_index=idx,
            colormap=Colormap(channel.colormap),
            clim=channel.contrast_limits or (0, 1),
            minmax=channel.contrast_limits or (0, 1),
        )


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


def color_for_colormap(cmap: Colormap) -> QtGui.QColor:
    """Get the representative color for the colormap."""
    return QtGui.QColor.fromRgbF(*cmap(0.5))
