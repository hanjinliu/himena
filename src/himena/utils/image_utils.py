from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import himena.standards.roi as _roi
    from himena.types import Rect
    from himena.standards.model_meta import ImageMeta
    from himena.data_wrappers import ArrayWrapper


def roi_2d_to_bbox(
    roi: _roi.Roi2D, arr: ArrayWrapper, is_rgb: bool = False
) -> Rect[int]:
    bbox = roi.bbox().adjust_to_int()
    xmax, ymax = slice_shape(arr, is_rgb)
    bbox = bbox.limit_to(xmax, ymax)
    if bbox.width <= 0 or bbox.height <= 0:
        raise ValueError("Crop range out of bounds.")
    return bbox


def bbox_to_slice(
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


def slice_shape(arr: ArrayWrapper, is_rgb: bool = False) -> tuple[int, int]:
    if is_rgb:
        return arr.shape[-2], arr.shape[-3]
    return arr.shape[-1], arr.shape[-2]
