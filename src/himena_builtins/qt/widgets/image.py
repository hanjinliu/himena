from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from typing import TYPE_CHECKING, Any, Callable, NamedTuple
import warnings
from qtpy import QtWidgets as QtW
from qtpy import QtGui, QtCore
import numpy as np
from cmap import Colormap
from pydantic_compat import BaseModel, Field
from superqt import ensure_main_thread

from himena.qt.magicgui._toggle_switch import QLabeledToggleSwitch
from himena_builtins.qt.widgets._image_components._roi_collection import (
    from_standard_roi,
)
from himena.consts import StandardType
from himena.standards import roi, model_meta
from himena.qt._utils import drag_model, qsignal_blocker
from himena.types import DragDataModel, DropResult, Size, WidgetDataModel
from himena.plugins import validate_protocol
from himena.widgets import set_status_tip
from himena.data_wrappers import ArrayWrapper, wrap_array
from himena_builtins.qt.widgets._image_components import (
    QImageGraphicsView,
    QRoi,
    QDimsSlider,
    QRoiButtons,
    QImageViewControl,
    QRoiCollection,
)
from himena_builtins.qt.widgets._splitter import QSplitterHandle
from himena_builtins.qt.widgets._shared import quick_min_max

if TYPE_CHECKING:
    from numpy.typing import NDArray
    from himena.style import Theme


class QImageView(QtW.QSplitter):
    """The default nD image viewer widget for himena.

    ## Basic Usage

    The image canvas can be interactively panned by dragging with the left mouse button,
    and zoomed by scrolling the mouse wheel. Zooming is reset by double-click. This
    widget also supports adding ROIs (Regions of Interest) to the image.

    - For multi-dimensional images, dimension sliders will be added to the bottom of the
      image canvas.
    - For multi-channel images, channel composition mode can be selected in the control
      widget. Toggle switches for each channel are available next to it.
    - The histogram of the current channel is displayed in the control widget. The
      contrast limits can be adjusted by dragging the handles on the histogram.
    - A ROI manager is in the right collapsible panel. Press the ROI buttons to switch
      between ROI modes.

    ## Keyboard Shortcuts

    - `L`: Switch between Line ROI and Segmented Line ROI.
    - `R`: Switch between Rectangle ROI and Rotated Rectangle ROI.
    - `E`: Switch to Ellipse ROI.
    - `G`: Switch to Polygon ROI.
    - `P`: Switch between Point ROI and Multi-Point ROI.
    - `Z`: Switch to Pan/Zoom Mode.
    - `Space`: Hold this key to temporarily switch to Pan/Zoom Mode.
    - `S`: Switch to Select Mode.
    - `T`: Add current ROI to the ROI list.
    - `V`: Toggle visibility of all the added ROIs.
    - `Delete` / `Backspace`: Remove the current ROI.
    - `Ctrl+A`: Select the entire image with a rectangle ROI.
    - `Ctrl+X`: Cut the selected ROI.
    - `Ctrl+C`: Copy the selected ROI.
    - `Ctrl+V`: Paste the copied ROI.
    - `Ctrl+D`: Duplicate the selected ROI.

    ## Drag and Drop

    - This widget accepts dropping models with `StandardType.IMAGE_ROIS` ("image-rois").
      Dropped ROIs will be added to the ROI list.
    - ROIs can be dragged out from the ROI manager. The type of the dragged model is
      `StandardType.IMAGE_ROIS` ("image-rois"). Use the drag indicator in the corner of
      the ROI list.
    """

    __himena_widget_id__ = "builtins:QImageView"
    __himena_display_name__ = "Built-in Image Viewer"
    _executor = ThreadPoolExecutor(max_workers=1)

    def __init__(self):
        super().__init__(QtCore.Qt.Orientation.Horizontal)

        widget_left = QtW.QWidget()
        self.addWidget(widget_left)
        layout = QtW.QVBoxLayout(widget_left)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        self._stick_grid_switch = QLabeledToggleSwitch()
        self._stick_grid_switch.setText("Stick to Grid")
        self._stick_grid_switch.setChecked(True)
        self._stick_grid_switch.setToolTip(
            "If checked, vertices of Rectangle and Ellipse ROIs will stick to the grid of the image."
        )
        self._img_view = QImageGraphicsView()
        self._roi_buttons = QRoiButtons(self)
        self._img_view.set_stick_to_grid(True)
        self._img_view.hovered.connect(self._on_hovered)
        self._img_view.roi_visibility_changed.connect(self._roi_visibility_changed)
        self._stick_grid_switch.toggled.connect(self._img_view.set_stick_to_grid)
        self._dims_slider = QDimsSlider()
        self._roi_col = QRoiCollection(self)
        self._roi_col.layout().insertWidget(0, self._roi_buttons)
        self._roi_col.layout().insertWidget(1, self._stick_grid_switch)
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
        self._is_editable = True
        # cached ImageTuples for display
        self._current_image_slices: list[ImageTuple] | None = None
        self._is_rgb = False  # whether the image is RGB
        self._channel_axis: int | None = None
        self._channels: list[ChannelInfo] | None = None
        self._model_type: str = StandardType.IMAGE
        self._pixel_unit: str = "a.u."
        self._extension_default: str = ".png"
        self._original_title: str | None = None
        self._last_slice_future: Future | None = None

    def createHandle(self):
        return QSplitterHandle(self)

    @validate_protocol
    def update_model(self, model: WidgetDataModel):
        arr = wrap_array(model.value)
        self._original_title = model.title
        is_initialized = self._arr is not None
        is_same_dimensionality = is_initialized and arr.ndim == self._arr.ndim
        is_same_array = is_initialized and (self._arr.arr is model.value)
        ndim_rem = arr.ndim - 2

        # override widget state if metadata is available
        meta0 = model_meta.ImageMeta(
            axes=arr.axis_names(),
            interpolation="nearest",
            is_rgb=False,
            unit="a.u.",
        )
        self._arr = arr
        if isinstance(meta := model.metadata, model_meta.ImageMeta):
            _update_meta(meta0, meta)
            if meta.is_rgb:
                ndim_rem -= 1

        self._is_rgb = meta0.is_rgb
        if is_initialized:
            sl_old = self._dims_slider.value()
        else:
            sl_old = None
        sl_0 = self._calc_current_indices(arr, meta0, is_same_dimensionality)
        is_sl_same = sl_0 == sl_old

        # update sliders
        if not is_same_array:
            self._dims_slider.set_dimensions(arr.shape, meta0.axes, is_rgb=self._is_rgb)
        with qsignal_blocker(self._dims_slider):
            self._dims_slider.setValue(sl_0)
        axis_names = [meta0.axes[i].name for i in range(self._dims_slider.count())]
        self._roi_col._qroi_list = self._roi_col._qroi_list.coerce_dimensions(
            axis_names
        )

        # update scale bar
        if (axes := meta0.axes) is not None:
            xaxis = axes[-2] if self._is_rgb else axes[-1]
            self._img_view._scale_bar_widget.update_scale_bar(
                scale=xaxis.scale, unit=xaxis.unit
            )

        # update channel info
        if meta0.channel_axis is None or meta0.is_rgb:
            nchannels = 1
        else:
            nchannels = arr.shape[meta0.channel_axis]

        self._img_view.set_n_images(nchannels)
        if meta0.is_rgb:
            self._channel_axis = None  # override channel axis for RGB images
        else:
            self._channel_axis = meta0.channel_axis

        with qsignal_blocker(self._control):
            self._control.update_for_state(
                is_rgb=self._is_rgb,
                nchannels=nchannels,
                dtype=arr.dtype,
            )

        self._init_channels(meta0, nchannels, arr.dtype)

        if is_same_array and is_sl_same and self._current_image_slices is not None:
            img_slices = self._current_image_slices
        else:
            img_slices = self._get_image_slices(sl_0, nchannels)
        self._update_channels(meta0, img_slices, nchannels, arr.dtype)
        if not meta0.skip_image_rerendering:
            self._set_image_slices(img_slices)
        roi_list = meta0.unwrap_rois()
        if len(roi_list) > 0:
            self._roi_col.clear()
            self._roi_col.extend_from_standard_roi_list(
                roi_list.coerce_dimensions(axis_names)
            )
        if meta0.current_roi:
            self._img_view.remove_current_item(reason="update_model")
            self._img_view.set_current_roi(
                from_standard_roi(meta0.current_roi, self._img_view._roi_pen)
            )
        self._control._interp_check_box.setChecked(meta0.interpolation == "linear")
        self._model_type = model.type
        self._pixel_unit = meta0.unit or ""
        if ext_default := model.extension_default:
            self._extension_default = ext_default
        return None

    @validate_protocol
    def update_value(self, val):
        arr = wrap_array(val)
        if arr.shape != self._arr.shape:
            raise ValueError(
                "`QImageView.update_value` does not support updating the array shape. "
                "Please use `update_model` with `WidgetDataModel` instead."
            )
        self._arr = arr
        self._reset_image()

    def _clim_for_ith_channel(self, img_slices: list[ImageTuple], ith: int):
        ar0, _ = img_slices[ith]
        if ar0.dtype.kind == "c":
            ar0 = self._control.complex_transform(ar0)
        return quick_min_max(ar0)

    def _init_channels(self, meta: model_meta.ImageMeta, nchannels: int, dtype):
        if len(meta.channels) != nchannels:
            ch0 = meta.channels[0]
            channels = [
                ch0.model_copy(update={"colormap": None, "contrast_limits": (0, 1)})
                for _ in range(nchannels)
            ]
        else:
            channels = [
                ch.model_copy(update={"contrast_limits": (0, 1)})
                for ch in meta.channels
            ]
        self._channels = [
            ChannelInfo.from_channel(i, c, dtype) for i, c in enumerate(channels)
        ]

    def _update_channels(
        self,
        meta: model_meta.ImageMeta,
        img_slices: list[ImageTuple],
        nchannels: int,
        dtype: np.dtype,
    ):
        # before calling ChannelInfo.from_channel, contrast_limits must be set
        if len(meta.channels) != nchannels:
            ch0 = meta.channels[0]
            ch0.contrast_limits = self._clim_for_ith_channel(img_slices, 0)
            channels = [
                ch0.model_copy(update={"colormap": None}) for _ in range(nchannels)
            ]
        else:
            channels = meta.channels
            for i, ch in enumerate(channels):
                if ch.contrast_limits is None:
                    ch.contrast_limits = self._clim_for_ith_channel(img_slices, i)
        self._channels = [
            ChannelInfo.from_channel(i, c, dtype) for i, c in enumerate(channels)
        ]
        if len(self._channels) == 1 and channels[0].colormap is None:
            # ChannelInfo.from_channel returns a single green colormap but it should
            # be gray for single channel images.
            self._channels[0].colormap = Colormap("gray")
        if self._composite_state() == "Comp.":
            self._control._channel_visibilities.set_channels(self._channels)

    def _calc_current_indices(
        self,
        arr_new: ArrayWrapper,
        meta0: model_meta.ImageMeta,
        is_same_dimensionality: bool,
    ):
        ndim_rem = arr_new.ndim - 3 if meta0.is_rgb else arr_new.ndim - 2
        if meta0.current_indices is not None:
            sl_0 = tuple(force_int(_i) for _i in meta0.current_indices[:ndim_rem])
        elif is_same_dimensionality:
            sl_0 = self._dims_slider.value()
        else:
            if meta0.axes:
                axis_names = [axis.name for axis in meta0.axes][:ndim_rem]
                sl_0 = tuple(
                    size // 2 if aname.lower() == "z" else 0
                    for aname, size in zip(axis_names, arr_new.shape)
                )
            else:
                sl_0 = (0,) * ndim_rem
        # the indices should be in the valid range
        return tuple(
            min(max(0, s), size - 1) for s, size in zip(sl_0, arr_new.shape[:ndim_rem])
        )

    @validate_protocol
    def to_model(self) -> WidgetDataModel:
        assert self._arr is not None

        if self._control._interp_check_box.isChecked():
            interp = "linear"
        else:
            interp = "nearest"
        channels = [
            model_meta.ImageChannel(
                name=ch.name, contrast_limits=ch.clim, colormap=ch.colormap.name
            )
            for ch in self._channels
        ]
        current_indices = self._dims_slider.value()
        current_slices = current_indices + (None, None)
        if item := self._img_view._current_roi_item:
            current_roi = item.toRoi()
        else:
            current_roi = None
        axes = self._dims_slider._to_image_axes()
        if self._is_rgb:
            axes.append(model_meta.ArrayAxis(name="RGB"))
        return WidgetDataModel(
            value=self._arr.arr,
            type=self.model_type(),
            extension_default=self._extension_default,
            metadata=model_meta.ImageMeta(
                current_indices=current_slices,
                axes=axes,
                channels=channels,
                channel_axis=self._channel_axis,
                current_roi=current_roi,
                rois=self._roi_col.to_standard_roi_list,
                is_rgb=self._is_rgb,
                interpolation=interp,
                unit=self._pixel_unit,
            ),
        )

    @validate_protocol
    def model_type(self) -> str:
        return self._model_type

    @validate_protocol
    def size_hint(self) -> tuple[int, int]:
        return 400, 400

    @validate_protocol
    def is_editable(self) -> bool:
        return self._is_editable

    @validate_protocol
    def set_editable(self, editable: bool):
        self._is_editable = editable

    @validate_protocol
    def control_widget(self) -> QImageViewControl:
        return self._control

    @validate_protocol
    def allowed_drop_types(self) -> list[str]:
        return [StandardType.ROIS, StandardType.IMAGE_LABELS]

    @validate_protocol
    def dropped_callback(self, model: WidgetDataModel):
        if model.type == StandardType.ROIS:
            if isinstance(roi_list := model.value, roi.RoiListModel):
                self._roi_col.extend_from_standard_roi_list(roi_list)
                self._img_view.clear_rois()
                self._update_rois()
            self._is_modified = True
            return DropResult(delete_input=False)
        elif model.type == StandardType.IMAGE_LABELS:
            raise NotImplementedError("Merging with labels is not implemented yet.")
        return None

    @validate_protocol
    def theme_changed_callback(self, theme: Theme):
        if theme.name.startswith("light"):
            color = QtGui.QColor(0, 0, 0)
        else:
            color = QtGui.QColor(255, 255, 255)
        self._roi_buttons._update_colors(color)

    @validate_protocol
    def widget_resized_callback(self, old: Size, new: Size):
        self._img_view.resize_event(old, new)

    @validate_protocol
    def widget_added_callback(self):
        self._img_view.auto_range()

    def setFocus(self):
        return self._img_view.setFocus()

    def leaveEvent(self, ev) -> None:
        self._control._hover_info.setText("")

    def _composite_state(self) -> str:
        return self._control._channel_mode_combo.currentText()

    def _roi_visibility_changed(self, show_rois: bool):
        with qsignal_blocker(self._roi_col):
            self._roi_col._roi_visible_btn.setChecked(show_rois)

    def _get_image_slices(
        self,
        value: tuple[int, ...],
        nchannels: int,
    ) -> list[ImageTuple]:
        """Get numpy arrays for each channel (None mean hide the channel)."""
        if self._channel_axis is None:
            return [ImageTuple(self._get_image_slice_for_channel(value))]

        img_slices = []
        check_states = self._control._channel_visibility()
        for i in range(nchannels):
            vis = i >= len(check_states) or check_states[i]
            sl = list(value)
            sl[self._channel_axis] = i
            img_slices.append(ImageTuple(self._get_image_slice_for_channel(sl), vis))
        return img_slices

    def _update_image_visibility(self, visible: list[bool]):
        slices = self._current_image_slices
        if slices is None:
            return
        for i, vis in enumerate(visible):
            if i < len(slices):
                slices[i] = ImageTuple(slices[i].arr, vis)
        self._set_image_slices(slices)

    def _get_image_slice_for_channel(
        self, value: tuple[int, ...]
    ) -> NDArray[np.number]:
        """Get numpy array for current channel."""
        return self._arr.get_slice(tuple(value))

    def _slider_changed(self, value: tuple[int, ...], *, force_sync: bool = False):
        if self._arr is None:
            return
        if self._last_slice_future:
            self._last_slice_future.cancel()  # cancel last task
        if force_sync:
            img_slices = self._get_image_slices(value, len(self._channels))
            self._set_image_slices(img_slices)
        else:
            # set slice asynchronously
            self._last_slice_future = self._executor.submit(
                self._get_image_slices, value, len(self._channels)
            )
            self._last_slice_future.add_done_callback(self._set_image_slices_async)

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
            self._control._histogram.set_hist_for_array(
                img,
                clim=channel.clim,
                is_rgb=self._is_rgb,
                color=color_for_colormap(channel.colormap),
            )
        if self._current_image_slices is not None:
            visible = self._current_image_slices[idx].visible
        else:
            visible = True
        self._current_image_slices[idx] = ImageTuple(img, visible)

    @ensure_main_thread
    def _set_image_slices_async(self, future: Future[list[ImageTuple]]):
        self._last_slice_future = None
        if future.cancelled():
            return
        imgs = future.result()
        self._set_image_slices(imgs)

    def _set_image_slices(self, imgs: list[ImageTuple]):
        """Set image slices using the channel information.

        This method is only used for updating the entire image slices. Channels must be
        correctly set before calling this method, as it uses the channel information to
        transform the image slices.
        """
        self._current_image_slices = imgs
        if self._channels is None:
            return
        with qsignal_blocker(self._control._histogram):
            for i, (imtup, ch) in enumerate(zip(imgs, self._channels)):
                if imtup.visible:
                    img = imtup.arr
                else:
                    img = None
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
            hist_arr_ref = imgs[idx].arr
            if hist_arr_ref.dtype.kind == "c":
                hist_arr_ref = self._control.complex_transform(hist_arr_ref)
            self._control._histogram.set_hist_for_array(
                hist_arr_ref,
                clim=ch_cur.clim,
                is_rgb=self._is_rgb,
                color=color_for_colormap(ch_cur.colormap),
            )
            self._update_rois()
            self._img_view.set_image_blending([im.visible for im in imgs])

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
            qroi.set_label(roi.default_roi_label(len(self._roi_col)))
        indices = self._dims_slider.value()
        self._roi_col.add(indices, qroi)
        set_status_tip(f"Added a {qroi._roi_type()} ROI")

    def _on_roi_removed(self, idx: int):
        indices = self._dims_slider.value()
        qroi = self._roi_col.pop_roi_in_slice(indices, idx)
        set_status_tip(f"Removed a {qroi._roi_type()} ROI")
        self._roi_col.set_selections([])

    def _reset_image(self):
        if self._channels is None:  # not initialized yet
            return
        imgs = self._get_image_slices(self._dims_slider.value(), len(self._channels))
        self._set_image_slices(imgs)

    def _on_hovered(self, pos: QtCore.QPointF):
        x, y = pos.x(), pos.y()
        if self._current_image_slices is None:
            return
        iy, ix = int(y), int(x)
        idx = self.current_channel().channel_index or 0
        cur_img = self._current_image_slices[idx]
        ny, nx, *_ = cur_img.arr.shape
        if 0 <= iy < ny and 0 <= ix < nx:
            if not cur_img.visible:
                self._control._hover_info.setText(f"x={x:.1f}, y={y:.1f} (invisible)")
                return
            intensity = cur_img.arr[int(y), int(x)]
            # NOTE: intensity could be an RGBA numpy array.
            if isinstance(intensity, np.ndarray) or self._arr.dtype.kind == "b":
                _int = str(intensity)
            else:
                fmt = self._control._histogram._line_low._value_fmt
                _int = format(intensity, fmt)
            if self._pixel_unit:
                _int += f" [{self._pixel_unit}]"
            self._control._hover_info.setText(f"x={x:.1f}, y={y:.1f}, value={_int}")
        else:
            self._control._hover_info.setText("")

    # forward key events to image graphics view
    def keyPressEvent(self, a0: QtGui.QKeyEvent | None) -> None:
        return self._img_view.keyPressEvent(a0)

    def keyReleaseEvent(self, a0: QtGui.QKeyEvent | None) -> None:
        return self._img_view.keyReleaseEvent(a0)

    def _run_drag_model(self, indices: list[int]):
        def make_model():
            rlist = self._roi_col.to_standard_roi_list(indices)
            axes = self._dims_slider._to_image_axes()
            return WidgetDataModel(
                value=rlist,
                type=StandardType.ROIS,
                title="ROIs",
                metadata=model_meta.ImageRoisMeta(axes=axes),
            )

        nrois = len(indices)
        _s = "" if nrois == 1 else "s"
        drag_model(
            model=DragDataModel(getter=make_model, type=StandardType.ROIS),
            desc=f"{nrois} ROI{_s}",
            source=self,
        )


class ChannelInfo(BaseModel):
    name: str = Field(...)
    clim: tuple[float, float] = Field((0.0, 1.0))
    colormap: Colormap = Field(default_factory=lambda: Colormap("gray"))
    channel_index: int | None = Field(None)

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
            false_color = (np.array(self.colormap(0.0).rgba) * 255).astype(np.uint8)
            true_color = (np.array(self.colormap(1.0).rgba) * 255).astype(np.uint8)
            arr_normed = np.where(arr[..., np.newaxis], true_color, false_color)
        elif cmax > cmin:
            arr = arr.clip(cmin, cmax)
            arr_normed = (self.colormap((arr - cmin) / (cmax - cmin)) * 255).astype(
                np.uint8
            )
        else:
            color = np.array(self.colormap(0.5).rgba8, dtype=np.uint8)
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
        dtype: np.dtype,
    ) -> ChannelInfo:
        input_clim = channel.contrast_limits
        if input_clim is None:
            raise ValueError("Contrast limits are not set.")
        if channel.colormap is None:
            colormap = Colormap(f"cmap:{_DEFAULT_COLORMAPS[idx % 6]}")
        else:
            colormap = Colormap(channel.colormap)
        return cls(
            name=channel.name or f"Ch {idx}",
            channel_index=idx,
            colormap=colormap,
            clim=channel.contrast_limits,
        )


class ImageTuple(NamedTuple):
    """A layer of image and its visibility."""

    arr: NDArray[np.number]
    visible: bool = True


_DEFAULT_COLORMAPS = ["green", "magenta", "cyan", "yellow", "red", "blue"]


def color_for_colormap(cmap: Colormap) -> QtGui.QColor:
    """Get the representative color for the colormap."""
    return QtGui.QColor.fromRgbF(*cmap(0.5))


def force_int(idx: Any) -> int:
    if isinstance(idx, int):
        return idx
    if hasattr(idx, "__index__"):
        return idx.__index__()
    warnings.warn(f"Cannot convert {idx} to int, using 0 instead.")
    return 0


def _update_meta(meta0: model_meta.ImageMeta, meta: model_meta.ImageMeta):
    if meta.rois:
        meta0.rois = meta.rois
    if meta.axes:
        meta0.axes = meta.axes
    if meta.is_rgb:
        meta0.is_rgb = meta.is_rgb
        meta0.interpolation = "linear"
    if meta.channel_axis is not None:
        meta0.channel_axis = meta.channel_axis
    if meta.current_indices:
        meta0.current_indices = meta.current_indices
    if meta.channels:
        meta0.channels = meta.channels
    if meta.current_roi:
        meta0.current_roi = meta.current_roi
    if meta.unit is not None:
        meta0.unit = meta.unit
    if meta.interpolation:
        meta0.interpolation = meta.interpolation
    meta0.skip_image_rerendering = meta.skip_image_rerendering
    return None
