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
    QRoiCollection,
    QImageViewSplitterHandle,
)

if TYPE_CHECKING:
    from numpy.typing import NDArray
    from himena.builtins.qt.widgets._image_components._graphics_view import Mode


class QImageView(QtW.QSplitter):
    """The default nD image viewer widget for himena."""

    __himena_widget_id__ = "builtins:QImageView"
    __himena_display_name__ = "Built-in Image Viewer"

    def __init__(self):
        super().__init__(QtCore.Qt.Orientation.Horizontal)
        self.setHandleWidth(8)

        widget_left = QtW.QWidget()
        self.addWidget(widget_left)
        layout = QtW.QVBoxLayout(widget_left)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        self._roi_buttons = QRoiButtons()
        self._roi_buttons.mode_changed.connect(self._on_roi_mode_changed)
        self._img_view = QImageGraphicsView()
        self._img_view.hovered.connect(self._on_hovered)
        self._img_view.mode_changed.connect(self._roi_buttons.set_mode)
        self._img_view.roi_visibility_changed.connect(self._roi_visibility_changed)
        self._dims_slider = QDimsSlider()
        self._roi_col = QRoiCollection()
        self._roi_col.show_rois_changed.connect(self._img_view.set_show_rois)
        self._roi_col.show_labels_changed.connect(self._img_view.set_show_labels)
        self._roi_col.key_pressed.connect(self._img_view.keyPressEvent)
        self._roi_col.key_released.connect(self._img_view.keyReleaseEvent)
        self._roi_col.roi_item_clicked.connect(self._roi_item_clicked)
        self._roi_col._add_btn.clicked.connect(self._img_view.add_current_roi)
        self._roi_col._remove_btn.clicked.connect(
            lambda: self._img_view.remove_current_item(remove_from_list=True)
        )
        self._roi_col.layout().insertWidget(0, self._roi_buttons)
        layout.addWidget(self._img_view)
        layout.addWidget(self._dims_slider)

        self._img_view.roi_added.connect(self._on_roi_added)
        self._img_view.roi_removed.connect(self._on_roi_removed)
        self._dims_slider.valueChanged.connect(self._slider_changed)

        self.addWidget(self._roi_col)
        self.setStretchFactor(0, 6)
        self.setStretchFactor(1, 1)
        self.setSizes([400, 0])
        self._control = QImageViewControl(self)
        self._arr: ArrayWrapper | None = None  # the internal array data for display
        self._is_modified = False  # whether the widget is modified
        self._current_image_slices = None  # cached numpy arrays for display
        self._is_rgb = False  # whether the image is RGB
        self._channel_axis: int | None = None
        self._channels: list[ChannelInfo] | None = None
        self._model_type = StandardType.IMAGE
        self._img_view.add_image_layer()

    def createHandle(self):
        return QImageViewSplitterHandle(QtCore.Qt.Orientation.Horizontal, self)

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
        meta0 = model_meta.ImageMeta(
            axes=arr.axis_names(),
            interpolation="linear" if _is_rgb else "nearest",
            is_rgb=_is_rgb,
        )
        self._arr = arr
        if isinstance(meta := model.metadata, model_meta.ImageMeta):
            # TODO: consider other attributes
            if meta.rois:
                meta0.rois = meta.rois
            if meta.interpolation:
                meta0.interpolation = meta.interpolation
            if meta.axes:
                meta0.axes = meta.axes
            if meta.is_rgb:
                meta0.is_rgb = meta.is_rgb
            if meta.channel_axis is not None:
                meta0.channel_axis = meta.channel_axis
            if meta.current_indices:
                meta0.current_indices = meta.current_indices
            if meta.channels:
                meta0.channels = meta.channels

        self._is_rgb = meta0.is_rgb
        if meta0.current_indices is not None:
            sl_0 = meta0.current_indices[:ndim_rem]
        elif is_initialized and is_same_dimensionality:
            sl_0 = self._dims_slider.value()
        else:
            if meta0.axes:
                axis_names = [axis.name for axis in meta0.axes][:ndim_rem]
                sl_0 = tuple(
                    size // 2 if aname.lower() == "z" else 0
                    for aname, size in zip(axis_names, arr.shape)
                )
            else:
                sl_0 = (0,) * ndim_rem
        # the indices should be in the valid range
        sl_0 = tuple(
            min(max(0, s), size - 1) for s, size in zip(sl_0, arr.shape[:ndim_rem])
        )

        # update sliders
        self._dims_slider.set_dimensions(arr.shape, meta0.axes, is_rgb=self._is_rgb)
        with qsignal_blocker(self._dims_slider):
            self._dims_slider.setValue(sl_0)

        # update channel info
        if meta0.channel_axis is None:
            nchannels = 1
        else:
            nchannels = arr.shape[meta0.channel_axis]

        self._img_view.set_n_images(nchannels)
        if _is_rgb:
            self._channel_axis = None  # override channel axis for RGB images
        else:
            self._channel_axis = meta0.channel_axis

        with qsignal_blocker(self._control):
            self._control.update_for_state(
                is_rgb=self._is_rgb,
                nchannels=nchannels,
                dtype=arr.dtype,
            )
        img_slices = self._get_image_slices(sl_0, nchannels)

        if self._channels is None:  # not initialized yet
            # before calling ChannelInfo.from_channel, contrast_limits must be set
            if len(meta0.channels) != nchannels:
                ch0 = meta0.channels[0]
                ch0.contrast_limits = self._clim_for_ith_channel(img_slices, 0)
                channels = [
                    ch0.model_copy(update={"colormap": None}) for _ in range(nchannels)
                ]
            else:
                channels = meta0.channels
                for i, ch in enumerate(channels):
                    if ch.contrast_limits is None:
                        ch.contrast_limits = self._clim_for_ith_channel(img_slices, i)
            self._channels = [
                ChannelInfo.from_channel(i, c) for i, c in enumerate(channels)
            ]
            if len(self._channels) == 1:
                self._channels[0].colormap = Colormap("gray")

        self._set_image_slices(img_slices)
        self._control._interp_check_box.setChecked(meta0.interpolation == "linear")
        self._model_type = model.type
        return None

    def _clim_for_ith_channel(self, img_slices, ith: int):
        if (ar0 := img_slices[ith]) is None:
            sl = self._dims_slider.value()
            if self._channel_axis is not None:
                sl = list(sl)
                sl[self._channel_axis] = ith
                sl = tuple(sl)
            ar0 = self._arr.get_slice(sl)
        return ar0.min(), ar0.max()

    @protocol_override
    def to_model(self) -> WidgetDataModel:
        assert self._arr is not None

        if self._control._interp_check_box.isChecked():
            interp = "linear"
        else:
            interp = "nearest"
        channels = [
            model_meta.ImageChannel(
                name=ch.name, contrast_limits=ch.clim, colormap=ch.colormap
            )
            for ch in self._channels
        ]
        _all = slice(None)
        current_indices = self._dims_slider.value()
        current_slices = current_indices + (_all, _all)
        if item := self._img_view._current_roi_item:
            current_roi = item.toRoi(current_indices)
        else:
            current_roi = None
        axes = self._dims_slider._to_image_axes()
        if self._is_rgb:
            axes.append(model_meta.ImageAxis(name="RGB"))
        return WidgetDataModel(
            value=self._arr.arr,
            type=self.model_type(),
            extension_default=".png",
            metadata=model_meta.ImageMeta(
                current_indices=current_slices,
                axes=axes,
                channels=channels,
                channel_axis=self._channel_axis,
                current_roi=current_roi,
                rois=self._roi_col.to_standard_roi_list,
                is_rgb=self._is_rgb,
                interpolation=interp,
            ),
        )

    @protocol_override
    def model_type(self) -> str:
        return self._model_type

    @protocol_override
    def size_hint(self) -> tuple[int, int]:
        return 400, 400

    @protocol_override
    def is_editable(self) -> bool:
        return False

    @protocol_override
    def control_widget(self) -> QtW.QWidget:
        return self._control

    @protocol_override
    def mergeable_model_types(self) -> list[str]:
        return [StandardType.IMAGE_ROIS, StandardType.IMAGE_LABELS]

    @protocol_override
    def merge_model(self, model: WidgetDataModel):
        if model.type == StandardType.IMAGE_ROIS:
            if isinstance(roi_list := model.value, roi.RoiListModel):
                self._roi_col.update_from_standard_roi_list(roi_list)
                self._img_view.clear_rois()
                self._update_rois()
            self._is_modified = True
        elif model.type == StandardType.IMAGE_LABELS:
            raise NotImplementedError("Merging with labels is not implemented yet.")
        return None

    def setFocus(self):
        return self._img_view.setFocus()

    def leaveEvent(self, ev) -> None:
        self._control._hover_info.setText("")

    def _composite_state(self) -> str:
        return self._control._channel_mode_combo.currentText()

    def _roi_item_clicked(self, indices: tuple[int, ...], qroi: QRoi):
        self._dims_slider.setValue(indices)
        self._img_view.select_item(qroi)

    def _roi_visibility_changed(self, show_rois: bool):
        with qsignal_blocker(self._roi_col):
            self._roi_col._roi_visible_btn.setChecked(show_rois)

    def _get_image_slices(
        self,
        value: tuple[int, ...],
        nchannels: int,
    ) -> list[NDArray[np.number] | None]:
        """Get numpy arrays for each channel (None mean hide the channel)."""
        if self._channel_axis is None:
            return [self._get_image_slice_for_channel(value)]

        if nchannels == 1 or self._composite_state() != "Comp.":
            img_slices = [None] * nchannels
            idx = value[self._channel_axis]
            img_slices[idx] = self._get_image_slice_for_channel(value)
        else:
            img_slices = []
            for i in range(nchannels):
                sl = list(value)
                sl[self._channel_axis] = i
                img_slices.append(self._get_image_slice_for_channel(sl))
        return img_slices

    def _get_image_slice_for_channel(
        self, value: tuple[int, ...]
    ) -> NDArray[np.number]:
        """Get numpy array for current channel."""
        # return None if the array is not visible
        return self._arr.get_slice(tuple(value))

    def _slider_changed(self, value: tuple[int, ...]):
        # `image_slice` given only when it is available (for performance)
        if self._arr is None:
            return
        img_slices = self._get_image_slices(value, len(self._channels))
        self._set_image_slices(img_slices)

    def _set_image_slice(self, img: NDArray[np.number], channel: ChannelInfo):
        idx = channel.channel_index or 0
        with qsignal_blocker(self._control._histogram):
            self._img_view.set_array(
                idx,
                channel.transform_image(
                    img,
                    complex_transform=self._control.complex_transform,
                    is_rgb=self._is_rgb,
                    is_gray=self._composite_state() == "Gray",
                ),
            )
            self._img_view.clear_rois()
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

        This method is only used for updating the entire image slices. Channels must be
        correctly set before calling this method, as it uses the channel information to
        transform the image slices.
        """
        self._current_image_slices = imgs
        if self._channels is None:
            return
        with qsignal_blocker(self._control._histogram):
            for i, (img, ch) in enumerate(zip(imgs, self._channels)):
                self._img_view.set_array(
                    i,
                    ch.transform_image(
                        img,
                        complex_transform=self._control.complex_transform,
                        is_rgb=self._is_rgb,
                        is_gray=self._composite_state() == "Gray",
                    ),
                )
            self._img_view.clear_rois()
            ch_cur = self.current_channel()
            idx = ch_cur.channel_index or 0
            self._control._histogram.set_hist_for_array(
                imgs[idx],
                ch_cur.clim,
                ch_cur.minmax,
                is_rgb=self._is_rgb,
                color=color_for_colormap(ch_cur.colormap),
            )
            self._update_rois()

    def _update_rois(self):
        rois = self._roi_col.get_rois_on_slice(self._dims_slider.value())
        self._img_view.extend_qrois(rois)

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

    def _on_roi_added(self, qroi: QRoi):
        if qroi.label() == "":
            qroi.setLabel(str(len(self._roi_col)))
        indices = self._dims_slider.value()
        self._roi_col.add(indices, qroi)
        set_status_tip(f"Added a {qroi._roi_type()} ROI")

    def _on_roi_removed(self, idx: int):
        indices = self._dims_slider.value()
        qroi = self._roi_col.pop_roi(indices, idx)
        set_status_tip(f"Removed a {qroi._roi_type()} ROI")

    def _on_roi_mode_changed(self, mode: Mode):
        self._img_view.switch_mode(mode)
        mode_name = mode.name.replace("_", " ")
        if mode_name.startswith("ROI "):
            mode_name = mode_name[4:]
        set_status_tip(f"Switched to {mode_name} mode.")

    def _reset_image(self):
        imgs = self._get_image_slices(self._dims_slider.value(), len(self._channels))
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
            else:
                fmt = self._control._histogram._line_low._value_fmt
                _int = format(intensity, fmt)
            self._control._hover_info.setText(f"x={x:.1f}, y={y:.1f}, value={_int}")
        else:
            self._control._hover_info.setText("")

    # forward key events to image graphics view
    def keyPressEvent(self, a0: QtGui.QKeyEvent | None) -> None:
        return self._img_view.keyPressEvent(a0)

    def keyReleaseEvent(self, a0: QtGui.QKeyEvent | None) -> None:
        return self._img_view.keyReleaseEvent(a0)


class ChannelInfo(BaseModel):
    name: str | None = Field(None)
    clim: tuple[float, float] = Field((0.0, 1.0))
    minmax: tuple[float, float] = Field((0.0, 1.0))
    colormap: Colormap = Field(default_factory=lambda: Colormap("gray"))
    channel_index: int | None = Field(None)

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
                return self.as_gray().transform_image(arr, complex_transform)
            return self.transform_image_2d(arr, complex_transform)

    def transform_image_2d(
        self,
        arr: NDArray[np.number] | None,
        complex_transform: Callable[[NDArray[np.complexfloating]], NDArray[np.number]],
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
            false_color = (np.array(self.colormap(0.0)) * 255).astype(np.uint8)
            true_color = (np.array(self.colormap(1.0)) * 255).astype(np.uint8)
            arr_normed = np.where(arr[..., np.newaxis], true_color, false_color)
        elif cmax > cmin:
            arr_normed = (self.colormap((arr - cmin) / (cmax - cmin)) * 255).astype(
                np.uint8
            )
        else:
            color = (np.array(self.colormap(0.5)) * 255).astype(np.uint8)
            arr_normed = np.empty(arr.shape + (4,), dtype=np.uint8)
            arr_normed[:] = color[np.newaxis, np.newaxis]
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
        if cmax == cmin:
            amp = 128
        else:
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
    def from_channel(
        cls,
        idx: int,
        channel: model_meta.ImageChannel,
    ) -> ChannelInfo:
        input_clim = channel.contrast_limits
        if input_clim is None:
            raise ValueError("Contrast limits are not set.")
        if channel.colormap is None:
            colormap = Colormap(f"cmap:{_DEFAULT_COLORMAPS[idx % 6]}")
        else:
            colormap = Colormap(channel.colormap)
        return cls(
            name=channel.name,
            channel_index=idx,
            colormap=colormap,
            clim=channel.contrast_limits,
            minmax=channel.contrast_limits,
        )


def guess_clim(
    arr: ArrayWrapper,
    channel_axis: int | None = None,
    channel_index: int | None = None,
    is_rgb: bool = False,
) -> tuple[float, float]:
    if is_rgb:
        return (0, 255)
    if arr.dtype.kind == "b":
        return (0, 1)
    if isinstance(np_ndarray := arr.arr, np.ndarray):
        if channel_axis is not None and channel_index is not None:
            np_ndarray = np_ndarray[(slice(None),) * channel_axis + (channel_index,)]
        if np_ndarray.size < 1e7:
            # not very large, just use min and max
            return np_ndarray.min(), np_ndarray.max()
        stride = np_ndarray.size // 1e7
        np_ndarray_raveled = np_ndarray.ravel()
        return np_ndarray_raveled[::stride].min(), np_ndarray_raveled[::stride].max()

    ndim = arr.ndim
    sl = [slice(None)] * ndim
    if channel_index is not None and channel_axis is not None:
        sl[channel_axis] = channel_index
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
    return clim_min, clim_max


_DEFAULT_COLORMAPS = ["green", "magenta", "cyan", "yellow", "red", "blue"]


def prep_channel_infos(num: int) -> list[ChannelInfo]:
    if num == 1:
        names = ["gray"]
    else:
        names = list(cycle(_DEFAULT_COLORMAPS))
    return [
        ChannelInfo(colormap=Colormap(f"cmap:{name}"), channel_index=idx)
        for idx, name in enumerate(names)
    ]


def color_for_colormap(cmap: Colormap) -> QtGui.QColor:
    """Get the representative color for the colormap."""
    return QtGui.QColor.fromRgbF(*cmap(0.5))


def pick_atleast_one_slice(
    img_slices: list[NDArray[np.number] | None],
) -> NDArray[np.number] | None:
    for img in img_slices:
        if img is not None:
            return img
    return None
