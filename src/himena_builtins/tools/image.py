from typing import TYPE_CHECKING, Any, SupportsIndex
import numpy as np
from himena._data_wrappers._array import wrap_array, ArrayWrapper
from himena.plugins import register_function, configure_gui, configure_submenu
from himena.types import Parametric, Rect, WidgetDataModel
from himena.consts import StandardType
from himena.standards.model_meta import (
    ArrayAxis,
    ImageMeta,
    roi as _roi,
)
from himena.widgets._wrapper import SubWindow
from himena_builtins.tools.array import _cast_meta, _make_getter

if TYPE_CHECKING:
    import numpy as np

configure_submenu("tools/image/roi", "ROI")
configure_submenu("/model_menu/roi", "ROI")


@register_function(
    types=StandardType.IMAGE,
    menus=["tools/image/roi", "/model_menu/roi"],
    command_id="builtins:crop-image",
    keybindings=["Ctrl+Shift+X"],
)
def crop_image(model: WidgetDataModel) -> WidgetDataModel:
    """Crop the image around the current ROI."""
    roi, meta = _get_current_roi_and_meta(model)
    arr = wrap_array(model.value)
    if isinstance(roi, _roi.ImageRoi2D):
        sl, bbox = _2d_roi_to_slices(roi, arr, meta)
        arr_cropped = arr[(...,) + sl]
    else:
        raise NotImplementedError
    meta_out = meta.without_rois()
    meta_out.current_roi = roi.shifted(-bbox.left, -bbox.top)
    return model.with_value(arr_cropped, metadata=meta_out)


@register_function(
    types=StandardType.IMAGE,
    menus=["tools/image/roi", "/model_menu/roi"],
    command_id="builtins:crop-image-multi",
)
def crop_image_multi(model: WidgetDataModel) -> WidgetDataModel:
    """Crop the image around the registered ROIs and return as a model stack."""
    meta = _cast_meta(model, ImageMeta)
    arr = wrap_array(model.value)
    rois = _resolve_roi_list_model(meta, copy=False)
    meta_out = meta.without_rois()
    cropped_models: list[WidgetDataModel] = []
    for i, roi in enumerate(rois):
        if not isinstance(roi, _roi.ImageRoi2D):
            continue
        sl, _ = _2d_roi_to_slices(roi, arr, meta)
        arr_cropped = arr[(...,) + sl]
        model_0 = model.with_value(
            arr_cropped, metadata=meta_out, title=f"ROI-{i} of {model.title}"
        )
        cropped_models.append(model_0)
    return WidgetDataModel(
        value=cropped_models,
        type=StandardType.MODELS,
        title=f"Cropped images from {model.title}",
    )


@register_function(
    title="Crop Image (nD) ...",
    types=StandardType.IMAGE,
    menus=["tools/image/roi", "/model_menu/roi"],
    command_id="builtins:crop-image-nd",
)
def crop_image_nd(win: SubWindow) -> Parametric:
    """Crop the image in nD."""
    from himena.qt._magicgui import SliderRangeGetter

    model = win.to_model()
    ndim = wrap_array(model.value).ndim
    meta = _cast_meta(model, ImageMeta)
    if (axes := meta.axes) is None:
        axes = [ArrayAxis(name=f"axis-{i}") for i in range(ndim)]
    index_yx_rgb = 2 + int(meta.is_rgb)
    if ndim < index_yx_rgb + 1:
        raise ValueError("Image only has 2D data.")

    conf_kwargs = {}
    for i, axis in enumerate(axes[:-index_yx_rgb]):
        conf_kwargs[axis.name] = {
            "widget_type": SliderRangeGetter,
            "getter": _make_getter(win, i),
            "label": axis.name,
        }

    @configure_gui(**conf_kwargs)
    def run_crop_image(**kwargs: tuple[int | None, int | None]):
        model = win.to_model()  # NOTE: need to re-fetch the model
        arr = wrap_array(model.value)
        roi, meta = _get_current_roi_and_meta(model)
        sl_nd = tuple(slice(x0, x1) for x0, x1 in kwargs.values())
        if isinstance(roi, _roi.ImageRoi2D):
            sl, _ = _2d_roi_to_slices(roi, arr, meta)
            sl = sl_nd + sl
            arr_cropped = arr[sl]
        else:
            raise NotImplementedError
        meta_out = meta.without_rois()
        meta_out.current_indices = None  # shape changed, need to reset
        return model.with_value(arr_cropped, metadata=meta_out)

    return run_crop_image


def _2d_roi_to_slices(
    roi: _roi.ImageRoi2D, arr: ArrayWrapper, meta: ImageMeta
) -> tuple[tuple[slice, ...], Rect[int]]:
    bbox = roi.bbox().adjust_to_int()
    if meta.is_rgb:
        bbox = bbox.limit_to(arr.shape[-2], arr.shape[-3])
    else:
        bbox = bbox.limit_to(arr.shape[-1], arr.shape[-2])
    if bbox.width <= 0 or bbox.height <= 0:
        raise ValueError("Crop range out of bounds.")
    ysl = slice(bbox.top, bbox.top + bbox.height)
    xsl = slice(bbox.left, bbox.left + bbox.width)
    if meta.is_rgb:
        sl = (ysl, xsl, slice(None))
    else:
        sl = (ysl, xsl)
    return sl, bbox


@register_function(
    title="Duplicate ROIs",
    types=StandardType.IMAGE,
    menus=["tools/image/roi", "/model_menu/roi"],
    command_id="builtins:duplicate-rois",
)
def duplicate_rois(model: WidgetDataModel) -> WidgetDataModel:
    """Duplicate the ROIs as a new window with the ROI data."""
    meta = _cast_meta(model, ImageMeta)
    rois = _resolve_roi_list_model(meta)
    return WidgetDataModel(
        value=rois,
        type=StandardType.IMAGE_ROIS,
        title=f"ROIs of {model.title}",
    )


@register_function(
    title="Set colormap ...",
    types=StandardType.IMAGE,
    menus=["tools/image/channels", "/model_menu/channels"],
    command_id="builtins:set-colormaps",
)
def set_colormaps(win: SubWindow) -> Parametric:
    from himena.qt._magicgui import ColormapEdit

    model = win.to_model()
    meta = _cast_meta(model, ImageMeta).model_copy()
    channel_names = _get_channel_names(meta, allow_single=True)
    current_channels = [ch.colormap for ch in meta.channels]
    colormap_defaults = [
        "gray", "green", "magenta", "cyan", "yellow", "red", "blue", "plasma",
        "viridis", "inferno", "imagej:fire", "imagej:HiLo", "imagej:ice", "matlab:jet",
        "matlab:hot",
    ],  # fmt: skip
    options = {
        f"ch_{i}": {
            "label": channel_names[i],
            "widget_type": ColormapEdit,
            "defaults": colormap_defaults,
            "value": current_channels[i],
        }
        for i in range(len(channel_names))
    }

    @configure_gui(gui_options=options, show_parameter_labels=len(channel_names) > 1)
    def set_cmaps(**kwargs):
        meta.channels = [
            ch.with_colormap(cmap) for ch, cmap in zip(meta.channels, kwargs.values())
        ]
        win.update_model(model.model_copy(update={"metadata": meta}))
        return None

    return set_cmaps


@register_function(
    title="Split channels",
    types=StandardType.IMAGE,
    menus=["tools/image/channels", "/model_menu/channels"],
    command_id="builtins:split-channels",
)
def split_channels(model: WidgetDataModel) -> list[WidgetDataModel]:
    """Split the channels of the image."""
    meta = _cast_meta(model, ImageMeta)
    arr = wrap_array(model.value)
    if meta.channel_axis is not None:
        c_axis = meta.channel_axis
        channel_labels = _get_channel_names(meta)
    elif meta.is_rgb:
        c_axis = arr.ndim - 1
        channel_labels = ["R", "G", "B"]
    else:
        raise ValueError("Image does not have a channel axis and is not RGB.")
    slice_chn = (slice(None),) * c_axis
    models: list[WidgetDataModel] = []
    for idx in range(arr.shape[c_axis]):
        arr_i = arr[slice_chn + (idx,)]
        meta_i = meta.get_one_axis(c_axis, idx)
        meta_i.is_rgb = False
        title = f"[{channel_labels[idx]}] {model.title}"
        models.append(model.with_value(arr_i, metadata=meta_i, title=title))
    return models


@register_function(
    title="Specify rectangle ...",
    types=StandardType.IMAGE,
    menus=["tools/image/roi", "/model_menu/roi"],
    command_id="builtins:roi-specify-rectangle",
)
def roi_specify_rectangle(win: SubWindow) -> Parametric:
    """Specify the coordinates of a rectangle ROI."""

    model = win.to_model()
    meta = _cast_meta(model, ImageMeta)
    if isinstance(roi := meta.current_roi, _roi.RectangleRoi):
        x0, y0, w0, h0 = roi.x, roi.y, roi.width, roi.height
    else:
        x0 = y0 = 0
        w0 = h0 = 10

    @configure_gui(
        preview=True,
        x={"value": x0},
        y={"value": y0},
        width={"value": w0},
        height={"value": h0},
    )
    def run_roi_specify_coordinates(x: float, y: float, width: float, height: float):
        model = win.to_model()
        meta = _cast_meta(model, ImageMeta)
        indices = _slider_indices(meta)
        meta.current_roi = _roi.RectangleRoi(
            indices=indices, x=x, y=y, width=width, height=height
        )
        win.update_model(model.model_copy(update={"metadata": meta}))

    return run_roi_specify_coordinates


@register_function(
    title="Specify ellipse ...",
    types=StandardType.IMAGE,
    menus=["tools/image/roi", "/model_menu/roi"],
    command_id="builtins:roi-specify-ellipse",
)
def roi_specify_ellipse(win: SubWindow) -> Parametric:
    """Specify the coordinates of an ellipse ROI."""

    model = win.to_model()
    meta = _cast_meta(model, ImageMeta)
    if isinstance(roi := meta.current_roi, _roi.EllipseRoi):
        x0, y0, w0, h0 = roi.x, roi.y, roi.width, roi.height
    else:
        x0 = y0 = 0
        w0 = h0 = 10

    @configure_gui(
        preview=True,
        x={"value": x0},
        y={"value": y0},
        width={"value": w0},
        height={"value": h0},
    )
    def run_roi_specify_coordinates(x: float, y: float, width: float, height: float):
        model = win.to_model()
        meta = _cast_meta(model, ImageMeta)
        indices = _slider_indices(meta)
        meta.current_roi = _roi.EllipseRoi(
            indices=indices, x=x, y=y, width=width, height=height
        )
        win.update_model(model.model_copy(update={"metadata": meta}))

    return run_roi_specify_coordinates


@register_function(
    title="Specify line ...",
    types=StandardType.IMAGE,
    menus=["tools/image/roi", "/model_menu/roi"],
    command_id="builtins:roi-specify-line",
)
def roi_specify_line(win: SubWindow) -> Parametric:
    """Specify the coordinates of a line ROI."""

    model = win.to_model()
    meta = _cast_meta(model, ImageMeta)
    if isinstance(roi := meta.current_roi, _roi.LineRoi):
        x1, y1, x2, y2 = roi.x1, roi.y1, roi.x2, roi.y2
    else:
        x1 = y1 = 0
        x2 = y2 = 10

    @configure_gui(
        preview=True,
        x1={"value": x1},
        y1={"value": y1},
        x2={"value": x2},
        y2={"value": y2},
    )
    def run_roi_specify_coordinates(x1: float, y1: float, x2: float, y2: float):
        model = win.to_model()
        meta = _cast_meta(model, ImageMeta)
        indices = _slider_indices(meta)
        meta.current_roi = _roi.LineRoi(indices=indices, x1=x1, y1=y1, x2=x2, y2=y2)
        win.update_model(model.model_copy(update={"metadata": meta}))

    return run_roi_specify_coordinates


def _get_consensus_axes(arrs: list[Any]) -> list[str]:
    axes_consensus: list[str] | None = None
    for arr in arrs:
        arr_wrapped = wrap_array(arr)
        if axes_consensus is None:
            axes_consensus = arr_wrapped.axis_names()
        elif axes_consensus != arr_wrapped.axis_names():
            raise ValueError("Images have different axes.")
    return axes_consensus


def _stack_and_insert_axis(
    arrs: list[Any],
    meta: ImageMeta,
    axis: str,
    axis_index: int,
) -> tuple[Any, ImageMeta]:
    arr_out = np.stack(arrs, axis=axis_index)
    if axes := meta.axes:
        axes = axes.copy()
        axes.insert(axis_index, ArrayAxis(name=axis))
    else:
        axes = None
    is_c_axis = axis.lower() in ("c", "channel")
    meta = meta.model_copy(
        update={
            "axes": axes,
            "channel_axis": axis_index if is_c_axis else None,
            "current_indices": None,
        }
    )
    return arr_out, meta


@configure_gui(
    images={"types": [StandardType.IMAGE]},
)
def run_merge_channels(
    images: list[WidgetDataModel],
    axis: str = "c",
) -> WidgetDataModel:
    if len(images) < 2:
        raise ValueError("At least two images are required.")
    meta = _cast_meta(images[0], ImageMeta)
    if meta.is_rgb:
        raise ValueError("Cannot merge RGB image.")
    if meta.channel_axis is not None:
        raise ValueError("Image already has a channel axis.")
    arrs = [m.value for m in images]
    axes_consensus = _get_consensus_axes(arrs)
    c_axis = _find_index_to_insert_axis(axis, axes_consensus)
    axes_consensus.insert(c_axis, axis)

    arr_out, meta = _stack_and_insert_axis(arrs, meta, axis, c_axis)
    # TODO: should colormaps be inherited?
    # colormaps = [_cast_meta(m, ImageMeta).channels[0].colormap for m in models]

    return images[0].with_value(
        arr_out, metadata=meta, title=f"[Merge] {images[0].title}"
    )


@register_function(
    title="Merge channels ...",
    menus=["tools/image/channels", "/model_menu/channels"],
    command_id="builtins:merge-channels",
)
def merge_channels() -> Parametric:
    """Stack images along the channel axis."""
    return run_merge_channels


@register_function(
    title="Stack images ...",
    menus=["tools/image"],
    command_id="builtins:stack-images",
)
def stack_images() -> Parametric:
    @configure_gui(images={"types": [StandardType.IMAGE]})
    def run_stack_images(
        images: list[WidgetDataModel],
        axis_name: str,
        axis_index: int | None = None,
    ) -> WidgetDataModel:
        if axis_name.title() in ("C", "Channel"):
            return run_merge_channels(images)
        if len(images) < 2:
            raise ValueError("At least two images are required.")
        meta = _cast_meta(images[0], ImageMeta)
        arrs = [m.value for m in images]
        axes_consensus = _get_consensus_axes(arrs)
        if axis_name == "":
            axis_name = _make_unique_axis_name(axes_consensus)
        if axis_index is None:
            axis_index = _find_index_to_insert_axis(axis_name, axes_consensus)
        axes_consensus.insert(axis_index, axis_name)
        arr_out, meta = _stack_and_insert_axis(arrs, meta, axis_name, axis_index)
        return images[0].with_value(
            arr_out, metadata=meta, title=f"[Stack] {images[0].title}"
        )

    return run_stack_images


def _get_current_roi_and_meta(
    model: WidgetDataModel,
) -> tuple[_roi.ImageRoi2D, ImageMeta]:
    meta = _cast_meta(model, ImageMeta)
    if not (roi := meta.current_roi):
        raise ValueError("ROI selection is required for this operation.")
    return roi, meta


def _get_channel_names(meta: ImageMeta, allow_single: bool = False) -> list[str]:
    idx = meta.channel_axis
    if idx is None:
        if allow_single:
            return ["Ch-0"]
        raise ValueError("Image does not have a channel axis.")
    return [ch.name for ch in meta.channels]


def _make_unique_axis_name(axes: list[str]) -> str:
    i = 0
    while (axis := f"axis-{i}") in axes:
        i += 1
    return axis


def _find_index_to_insert_axis(axis: str, axes: list[str]) -> int:
    if axis in axes:
        raise ValueError(f"Axis '{axis}' already exists in axes: {axes!r}")
    _order_map = {"t": 0, "time": 0, "z": 1, "c": 2, "channel": 2}
    yx_axes_start_index = min(2, len(axes))
    # last axes are usually y, x
    axes_ref = [axis] + axes[:-yx_axes_start_index]
    axes_sorted = sorted(axes_ref, key=lambda x: _order_map.get(x.lower(), -1))
    return axes_sorted.index(axis)


def _slider_indices(meta: ImageMeta) -> tuple[int, ...]:
    if meta.current_indices:
        indices = tuple(i for i in meta.current_indices if isinstance(i, SupportsIndex))
    else:
        indices = ()
    return indices


def _resolve_roi_list_model(meta: ImageMeta, copy: bool = True) -> _roi.RoiListModel:
    rois = meta.rois
    if isinstance(rois, _roi.RoiListModel):
        if copy:
            rois = rois.model_copy()
    elif callable(rois):
        rois = rois()
        if not isinstance(rois, _roi.RoiListModel):
            raise ValueError(f"Expected a RoiListModel, got {type(rois)}")
    else:
        raise ValueError("Expected a RoiListModel or a factory function.")
    return rois
