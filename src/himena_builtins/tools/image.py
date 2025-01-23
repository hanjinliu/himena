from typing import Any, Literal, SupportsIndex
import numpy as np
from cmap import Colormap
from himena._data_wrappers._array import wrap_array, ArrayWrapper
from himena.plugins import (
    register_function,
    configure_gui,
    configure_submenu,
)
from himena.types import Parametric, WidgetDataModel
from himena.consts import StandardType
from himena.standards.model_meta import (
    ArrayAxis,
    ArrayMeta,
    ImageMeta,
    ImageRoisMeta,
    roi as _roi,
)
from himena.widgets._wrapper import SubWindow
from himena_builtins.tools.array import _cast_meta, _make_index_getter

configure_submenu("tools/image/roi", "ROI")
configure_submenu("/model_menu/roi", "ROI")


@register_function(
    types=StandardType.IMAGE,
    menus=["tools/image/roi", "/model_menu/roi"],
    command_id="builtins:image-crop:crop-image",
    keybindings=["Ctrl+Shift+X"],
)
def crop_image(model: WidgetDataModel) -> Parametric:
    """Crop the image around the current ROI."""
    arr = wrap_array(model.value)

    def _get_xy():
        roi, meta = _get_current_roi_and_meta(model)
        if not isinstance(roi, _roi.Roi2D):
            raise NotImplementedError
        left, top, width, height = _2d_roi_to_bbox(roi, arr, meta)
        x = left, left + width
        y = top, top + height
        return {"y": y, "x": x}

    @configure_gui(run_immediately_with=_get_xy)
    def run_crop_image(y: tuple[int, int], x: tuple[int, int]):
        xsl, ysl = slice(*x), slice(*y)
        meta = _cast_meta(model, ImageMeta)
        if meta.is_rgb:
            sl = (ysl, xsl, slice(None))
        else:
            sl = (ysl, xsl)
        arr_cropped = arr[(...,) + sl]
        meta_out = meta.without_rois()
        return model.with_value(
            arr_cropped.arr, metadata=meta_out
        ).with_title_numbering()

    return run_crop_image


@register_function(
    types=StandardType.IMAGE,
    menus=["tools/image/roi", "/model_menu/roi"],
    command_id="builtins:image-crop:crop-image-multi",
)
def crop_image_multi(model: WidgetDataModel) -> Parametric:
    """Crop the image around the registered ROIs and return as a model stack."""
    meta = _cast_meta(model, ImageMeta)
    arr = wrap_array(model.value)

    def _get_bbox_list():
        rois = meta.unwrap_rois()
        bbox_list: list[tuple[int, int, int, int]] = []
        for i, roi in enumerate(rois):
            if not isinstance(roi, _roi.Roi2D):
                continue
            bbox = _2d_roi_to_bbox(roi, arr, meta)
            bbox_list.append(bbox)
        return {"bbox_list": bbox_list}

    @configure_gui(run_immediately_with=_get_bbox_list)
    def run_crop_image_multi(bbox_list: list[tuple[int, int, int, int]]):
        meta_out = meta.without_rois()
        cropped_models: list[WidgetDataModel] = []
        for i, bbox in enumerate(bbox_list):
            sl = _bbox_to_slice(bbox, meta)
            arr_cropped = arr[(...,) + sl]
            model_0 = model.with_value(
                arr_cropped.arr, metadata=meta_out, title=f"ROI-{i} of {model.title}"
            )
            cropped_models.append(model_0)
        return WidgetDataModel(
            value=cropped_models,
            type=StandardType.MODELS,
            title=f"Cropped images from {model.title}",
        ).with_title_numbering()

    return run_crop_image_multi


@register_function(
    title="Crop Image (nD) ...",
    types=StandardType.IMAGE,
    menus=["tools/image/roi", "/model_menu/roi"],
    command_id="builtins:image-crop:crop-image-nd",
)
def crop_image_nd(win: SubWindow) -> Parametric:
    """Crop the image in nD, by drawing a 2D ROI and reading slider values."""
    from himena.qt.magicgui import SliderRangeGetter

    model = win.to_model()
    ndim = wrap_array(model.value).ndim
    meta = _cast_meta(model, ImageMeta)
    if ndim < 2:
        raise ValueError("Cannot crop image less than 2D.")
    axes_kwarg_names = [f"axis_{i}" for i in range(ndim)]
    index_yx_rgb = 2 + int(meta.is_rgb)
    if ndim < index_yx_rgb + 1:
        raise ValueError("Image only has 2D data.")

    conf_kwargs = {}
    for i, axis_name in enumerate(axes_kwarg_names[:-index_yx_rgb]):
        conf_kwargs[axis_name] = {
            "widget_type": SliderRangeGetter,
            "getter": _make_index_getter(win, i),
            "label": axis_name,
        }
    axis_y, axis_x = axes_kwarg_names[ndim - index_yx_rgb : ndim - index_yx_rgb + 2]
    conf_kwargs[axis_y] = {"bind": _make_roi_limits_getter(win, "y")}
    conf_kwargs[axis_x] = {"bind": _make_roi_limits_getter(win, "x")}

    @configure_gui(**conf_kwargs)
    def run_crop_image(**kwargs: tuple[int | None, int | None]):
        model = win.to_model()  # NOTE: need to re-fetch the model
        arr = wrap_array(model.value)
        sl_nd = tuple(slice(x0, x1) for x0, x1 in kwargs.values())
        arr_cropped = arr[sl_nd]
        meta_out = meta.without_rois()
        meta_out.current_indices = None  # shape changed, need to reset
        return model.with_value(arr_cropped.arr, metadata=meta_out)

    return run_crop_image


def _2d_roi_to_bbox(
    roi: _roi.Roi2D, arr: ArrayWrapper, meta: ImageMeta
) -> tuple[int, int, int, int]:
    bbox = roi.bbox().adjust_to_int()
    xmax, ymax = _slice_shape(arr, meta)
    bbox = bbox.limit_to(xmax, ymax)
    if bbox.width <= 0 or bbox.height <= 0:
        raise ValueError("Crop range out of bounds.")
    return tuple(bbox)


def _bbox_to_slice(
    bbox: tuple[int, int, int, int], meta: ImageMeta
) -> tuple[slice, ...]:
    left, top, width, height = bbox
    ysl = slice(top, top + height)
    xsl = slice(left, left + width)
    if meta.is_rgb:
        sl = (ysl, xsl, slice(None))
    else:
        sl = (ysl, xsl)
    return sl


def _make_roi_limits_getter(win: SubWindow, dim: Literal["x", "y"]):
    def _getter():
        model = win.to_model()
        meta = _cast_meta(model, ImageMeta)
        roi = meta.current_roi
        arr = wrap_array(model.value)
        if not isinstance(roi, _roi.Roi2D):
            raise NotImplementedError
        left, top, width, height = _2d_roi_to_bbox(roi, arr, meta)
        if dim == "x":
            return left, left + width
        return top, top + height

    return _getter


@register_function(
    title="Duplicate ROIs",
    types=StandardType.IMAGE,
    menus=["tools/image/roi", "/model_menu/roi"],
    command_id="builtins:duplicate-rois",
)
def duplicate_rois(model: WidgetDataModel) -> WidgetDataModel:
    """Duplicate the ROIs as a new window with the ROI data."""
    if isinstance(meta := model.metadata, ArrayMeta):
        axes = meta.axes
    else:
        axes = None
    return WidgetDataModel(
        value=_get_rois_from_model(model),
        type=StandardType.ROIS,
        title=f"ROIs of {model.title}",
        metadata=ImageRoisMeta(axes=axes),
    )


@register_function(
    title="Filter ROIs",
    types=StandardType.ROIS,
    menus=["/model_menu"],
    command_id="builtins:filter-rois",
)
@register_function(
    title="Filter ROIs",
    types=StandardType.IMAGE,
    menus=["tools/image/roi", "/model_menu/roi"],
    command_id="builtins:filter-image-rois",
)
def filter_rois(model: WidgetDataModel) -> Parametric:
    rois = _get_rois_from_model(model)
    _choices = [
        "Rectangle", "RotatedRectangle", "Line", "SegmentedLine", "Point2D", "Points2D",
        "Ellipse", "Rotated Ellipse", "Polygon"
    ]  # fmt: skip

    @configure_gui(types={"choices": _choices, "widget_type": "Select"})
    def run_filter_rois(types: list[str]):
        types_allowed = {_roi.pick_roi_model(typ.lower()) for typ in types}
        sl = [i for i, r in enumerate(rois) if type(r) in types_allowed]
        value = rois.filter_by_selection(sl)
        if isinstance(meta := model.metadata, (ImageRoisMeta, ImageMeta)):
            axes = meta.axes
        else:
            axes = None
        return WidgetDataModel(
            value=value,
            type=StandardType.ROIS,
            title=f"{model.title} filtered",
            metadata=ImageRoisMeta(axes=axes),
        )

    return run_filter_rois


@register_function(
    title="Select ROIs",
    types=StandardType.ROIS,
    menus=["/model_menu"],
    command_id="builtins:select-rois",
)
def select_rois(model: WidgetDataModel) -> Parametric:
    """Make a new ROI list with the selected ROIs."""
    rois = _get_rois_from_model(model)
    if not isinstance(meta := model.metadata, ImageRoisMeta):
        raise ValueError(f"Expected an ImageRoisMeta metadata, got {type(meta)}")
    axes = meta.axes

    def _get_selections():
        return {"selections": meta.selections}

    @configure_gui(run_immediately_with=_get_selections)
    def run_select(selections: list[int]) -> WidgetDataModel:
        if len(selections) == 0:
            raise ValueError("No ROIs selected.")

        return WidgetDataModel(
            value=rois.filter_by_selection(selections),
            type=StandardType.ROIS,
            title=f"Subset of {model.title}",
            metadata=ImageRoisMeta(axes=axes),
        )

    return run_select


@register_function(
    title="Point ROIs to DataFrame",
    types=StandardType.ROIS,
    menus=["/model_menu"],
    command_id="builtins:point-rois-to-dataframe",
)
@register_function(
    title="Point ROIs to DataFrame",
    types=StandardType.IMAGE,
    menus=["tools/image/roi", "/model_menu/roi"],
    command_id="builtins:image:point-rois-to-dataframe",
)
def point_rois_to_dataframe(model: WidgetDataModel) -> WidgetDataModel:
    rois = _get_rois_from_model(model)
    if len(rois) == 0:
        raise ValueError("No ROIs to convert")
    ndim = rois.indices.shape[1] + 2
    arrs: list[np.ndarray] = []
    for indices, roi in rois.iter_with_indices():
        if isinstance(roi, _roi.PointRoi2D):
            arr = np.array([indices + (roi.y, roi.x)], dtype=np.float32)
        elif isinstance(roi, _roi.PointsRoi2D):
            npoints = len(roi.xs)
            arr = np.empty((npoints, ndim))
            arr[:, :-2] = indices
            arr[:, -2] = roi.ys
            arr[:, -1] = roi.xs
        else:
            raise TypeError(f"Expected a PointRoi or PointsRoi, got {type(roi)}")
        arrs.append(arr)
    arr_all = np.concatenate(arrs, axis=0)
    axes = None
    if isinstance(meta := model.metadata, (ArrayMeta, ImageRoisMeta)):
        axes = meta.axes
    if axes is None:
        axes = [ArrayAxis(name=f"axis-{i}") for i in range(ndim)]
    out = {axis.name: arr_all[:, i] for i, axis in enumerate(axes)}
    return WidgetDataModel(
        value=out,
        type=StandardType.DATAFRAME,
        title=f"Points of {model.title}",
    )


@register_function(
    title="Set colormap ...",
    types=StandardType.IMAGE,
    menus=["tools/image/channels", "/model_menu/channels"],
    command_id="builtins:set-colormaps",
)
def set_colormaps(win: SubWindow) -> Parametric:
    from himena.qt.magicgui import ColormapEdit

    model = win.to_model()
    meta = _cast_meta(model, ImageMeta).model_copy()
    channel_names = _get_channel_names(meta, allow_single=True)
    current_channels = [ch.colormap for ch in meta.channels]
    colormap_defaults = [
        "gray", "green", "magenta", "cyan", "yellow", "red", "blue", "plasma",
        "viridis", "inferno", "imagej:fire", "imagej:HiLo", "imagej:ice", "matlab:jet",
        "matlab:hot",
    ]  # fmt: skip
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
    def set_cmaps(**kwargs: str):
        meta.channels = [
            ch.with_colormap(Colormap(cmap).name)
            for ch, cmap in zip(meta.channels, kwargs.values())
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
    """Split the image by the channel axis into separate images."""
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
    command_id="builtins:image-specify:roi-specify-rectangle",
)
def roi_specify_rectangle(win: SubWindow) -> Parametric:
    """Specify the coordinates of a rectangle ROI."""

    model = win.to_model()
    meta = _cast_meta(model, ImageMeta)
    if isinstance(roi := meta.current_roi, _roi.RectangleRoi):
        x0, y0, w0, h0 = roi.x, roi.y, roi.width, roi.height
    else:
        nx, ny = _slice_shape(wrap_array(model.value), meta)
        x0, y0 = nx / 4, ny / 4
        w0, h0 = nx / 2, ny / 2

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
        meta.skip_image_rerendering = True
        win.update_model(model.model_copy(update={"metadata": meta}))

    return run_roi_specify_coordinates


@register_function(
    title="Specify ellipse ...",
    types=StandardType.IMAGE,
    menus=["tools/image/roi", "/model_menu/roi"],
    command_id="builtins:image-specify:roi-specify-ellipse",
)
def roi_specify_ellipse(win: SubWindow) -> Parametric:
    """Specify the coordinates of an ellipse ROI."""

    model = win.to_model()
    meta = _cast_meta(model, ImageMeta)
    if isinstance(roi := meta.current_roi, _roi.EllipseRoi):
        x0, y0, w0, h0 = roi.x, roi.y, roi.width, roi.height
    else:
        nx, ny = _slice_shape(wrap_array(model.value), meta)
        x0, y0 = nx / 4, ny / 4
        w0, h0 = nx / 2, ny / 2

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
        meta.skip_image_rerendering = True
        win.update_model(model.model_copy(update={"metadata": meta}))

    return run_roi_specify_coordinates


@register_function(
    title="Specify line ...",
    types=StandardType.IMAGE,
    menus=["tools/image/roi", "/model_menu/roi"],
    command_id="builtins:image-specify:roi-specify-line",
)
def roi_specify_line(win: SubWindow) -> Parametric:
    """Specify the coordinates of a line ROI."""

    model = win.to_model()
    meta = _cast_meta(model, ImageMeta)
    if isinstance(roi := meta.current_roi, _roi.LineRoi):
        x1, y1, x2, y2 = roi.x1, roi.y1, roi.x2, roi.y2
    else:
        nx, ny = _slice_shape(wrap_array(model.value), meta)
        x1, y1 = nx / 4, ny / 4
        x2, y2 = nx / 4 * 3, ny / 4 * 3

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
        meta.skip_image_rerendering = True
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
) -> tuple[_roi.Roi2D, ImageMeta]:
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


def _get_rois_from_model(model: WidgetDataModel) -> _roi.RoiListModel:
    if model.type == StandardType.IMAGE:
        meta = _cast_meta(model, ImageMeta)
        rois = meta.unwrap_rois()
    elif model.type == StandardType.ROIS:
        rois = model.value
    else:
        raise ValueError(
            "Command can only be executed on an 'image' or 'image-rois' model."
        )
    return rois


def _slice_shape(arr: ArrayWrapper, meta: ImageMeta) -> tuple[int, int]:
    if meta.is_rgb:
        return arr.shape[-2], arr.shape[-3]
    return arr.shape[-1], arr.shape[-2]
