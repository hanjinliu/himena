from __future__ import annotations

import math
from typing import TYPE_CHECKING, Any
import numpy as np
from pydantic_compat import BaseModel, Field, field_validator
from pydantic import PrivateAttr
from himena.types import Rect

if TYPE_CHECKING:
    from numpy.typing import NDArray
    from typing import Self


class ImageRoi(BaseModel):
    """Base class for ROIs (Region of Interest) in images."""

    name: str | None = Field(None, description="Name of the ROI.")

    def model_dump_typed(self) -> dict:
        return {"type": type(self).__name__.lower(), **self.model_dump()}

    @classmethod
    def construct(cls, typ: str, dict_: dict) -> ImageRoi:
        if typ == "rectangle":
            return RectangleRoi.model_validate(dict_)
        if typ == "rotatedrectangle":
            return RotatedRectangleRoi.model_validate(dict_)
        if typ == "ellipse":
            return EllipseRoi.model_validate(dict_)
        if typ == "rotatedellipse":
            return RotatedEllipseRoi.model_validate(dict_)
        if typ == "points":
            return PointsRoi.model_validate(dict_)
        if typ == "segmentedline":
            return SegmentedLineRoi.model_validate(dict_)
        if typ == "polygon":
            return PolygonRoi.model_validate(dict_)
        if typ == "line":
            return LineRoi.model_validate(dict_)
        raise ValueError(f"Unknown ROI type: {typ!r}")


class ImageRoiND(ImageRoi):
    indices: tuple[int, ...] = Field(
        default=(), description="Indices of the ROI in the >nD dimensions."
    )

    def flattened(self) -> Self:
        """Return a copy of the ROI with indices flattened."""
        return self.model_copy(update={"indices": ()})


class ImageRoi2D(ImageRoiND):
    def bbox(self) -> Rect[float]:
        """Return the bounding box of the ROI."""
        raise NotImplementedError


class ImageRoi3D(ImageRoiND):
    pass


class RectangleRoi(ImageRoi2D):
    """ROI that represents a rectangle."""

    x: float = Field(..., description="X-coordinate of the top-left corner.")
    y: float = Field(..., description="Y-coordinate of the top-left corner.")
    width: float = Field(..., description="Width of the rectangle.")
    height: float = Field(..., description="Height of the rectangle.")

    def shifted(self, dx: float, dy: float) -> RectangleRoi:
        """Return a new rectangle shifted by the given amount."""
        return self.model_copy(update={"x": self.x + dx, "y": self.y + dy})

    def area(self) -> float:
        return self.width * self.height

    def bbox(self) -> Rect[float]:
        return Rect(self.x, self.y, self.width, self.height)


class RotatedRoi2D(ImageRoi2D):
    angle: float = Field(..., description="Counter-clockwise angle in degrees.")


class RotatedRectangleRoi(RectangleRoi, RotatedRoi2D):
    """ROI that represents a rotated rectangle."""

    def bbox(self) -> Rect[float]:
        ang = math.radians(self.angle)
        rot = np.array(
            [[math.cos(ang), math.sin(ang)], [-math.sin(ang), math.cos(ang)]]
        )
        vecx = np.array([self.width, 0]) @ rot
        vecy = np.array([0, self.height]) @ rot
        top = min(0, vecx[0], vecx[0] + vecy[0], vecy[0])
        bottom = max(0, vecx[0], vecx[0] + vecy[0], vecy[0])
        left = min(0, vecx[1], vecx[1] + vecy[1], vecy[1])
        right = max(0, vecx[1], vecx[1] + vecy[1], vecy[1])
        width = right - left
        height = bottom - top
        return Rect(left, top, width, height)


class EllipseRoi(ImageRoi2D):
    """ROI that represents an ellipse."""

    x: float = Field(..., description="X-coordinate of the center.")
    y: float = Field(..., description="Y-coordinate of the center.")
    width: float = Field(..., description="Diameter along the x-axis.")
    height: float = Field(..., description="Diameter along the y-axis.")

    def shifted(self, dx: float, dy: float) -> EllipseRoi:
        return self.model_copy(update={"x": self.x + dx, "y": self.y + dy})

    def area(self) -> float:
        return math.pi * self.width * self.height / 4

    def circumference(self) -> float:
        a, b = self.width / 2, self.height / 2
        return math.pi * (3 * (a + b) - math.sqrt((3 * a + b) * (a + 3 * b)))

    def eccentricity(self) -> float:
        a, b = self.width / 2, self.height / 2
        return math.sqrt(1 - b**2 / a**2)

    def bbox(self) -> Rect[float]:
        return Rect(self.x, self.y, self.width, self.height)


class RotatedEllipseRoi(EllipseRoi, RotatedRoi2D):
    """ROI that represents a rotated ellipse."""


class PointRoi(ImageRoi2D):
    """ROI that represents a single point."""

    x: float = Field(..., description="X-coordinate of the point.")
    y: float = Field(..., description="Y-coordinate of the point.")

    def shifted(self, dx: float, dy: float) -> PointRoi:
        return self.model_copy(
            update={
                "x": self.x + dx,
                "y": self.y + dy,
            }
        )

    def bbox(self) -> Rect[float]:
        return Rect(self.x, self.y, 0, 0)


class PointsRoi(ImageRoi2D):
    """ROI that represents a set of points."""

    xs: Any = Field(..., description="List of x-coordinates.")
    ys: Any = Field(..., description="List of y-coordinates.")

    @field_validator("xs", "ys")
    def _validate_np_arrays(cls, v) -> NDArray[np.number]:
        out = np.asarray(v)
        if out.dtype.kind not in "if":
            raise ValueError("Must be a numerical array.")
        return out

    def shifted(self, dx: float, dy: float) -> PointsRoi:
        return self.model_copy(update={"xs": self.xs + dx, "ys": self.ys + dy})

    def bbox(self) -> Rect[float]:
        xmin, xmax = np.min(self.xs), np.max(self.xs)
        ymin, ymax = np.min(self.ys), np.max(self.ys)
        return Rect(xmin, ymin, xmax - xmin, ymax - ymin)


class SegmentedLineRoi(PointsRoi):
    """ROI that represents a segmented line."""

    def length(self) -> float:
        return np.sum(np.hypot(np.diff(self.xs), np.diff(self.ys)))


class PolygonRoi(SegmentedLineRoi):
    """ROI that represents a closed polygon."""


class SplineRoi(ImageRoi2D):
    """ROI that represents a spline curve."""

    degree: int = Field(3, description="Degree of the spline curve.", ge=1)


class LineRoi(ImageRoi):
    x1: float = Field(..., description="X-coordinate of the first point.")
    y1: float = Field(..., description="Y-coordinate of the first point.")
    x2: float = Field(..., description="X-coordinate of the second point.")
    y2: float = Field(..., description="Y-coordinate of the second point.")

    def shifted(self, dx: float, dy: float) -> LineRoi:
        return LineRoi(
            x1=self.x1 + dx,
            y1=self.y1 + dy,
            x2=self.x2 + dx,
            y2=self.y2 + dy,
        )

    def length(self) -> float:
        """Length of the line."""
        return math.hypot(self.x2 - self.x1, self.y2 - self.y1)

    def degree(self) -> float:
        """Angle in degrees."""
        return math.degrees(math.atan2(self.y2 - self.y1, self.x2 - self.x1))

    def radian(self) -> float:
        """Angle in radians."""
        return math.atan2(self.y2 - self.y1, self.x2 - self.x1)

    def linspace(self, num: int) -> NDArray[np.float64]:
        """Return a tuple of x and y coordinates of np.linspace along the line."""
        return np.linspace(self.x1, self.x2, num), np.linspace(self.y1, self.y2, num)

    def arange(self, step: float) -> NDArray[np.float64]:
        """Return a tuple of x and y coordinates of np.arange along the line."""
        radian = self.radian()
        num, rem = divmod(self.length(), step)
        xrem = rem * math.cos(radian)
        yrem = rem * math.sin(radian)
        return (
            np.linspace(self.x1, self.x2 - xrem, int(num)),
            np.linspace(self.y1, self.y2 - yrem, int(num)),
        )

    def bbox(self) -> Rect[float]:
        xmin, xmax = min(self.x1, self.x2), max(self.x1, self.x2)
        ymin, ymax = min(self.y1, self.y2), max(self.y1, self.y2)
        return Rect(xmin, ymin, xmax - xmin, ymax - ymin)


class RoiListModel(BaseModel):
    """List of ROIs, with useful methods."""

    rois: list[ImageRoi] = Field(default_factory=list, description="List of ROIs.")
    _slice_cache: dict[tuple[int, ...], list[ImageRoi]] = PrivateAttr(
        default_factory=dict
    )

    def model_dump_typed(self) -> dict:
        return {"type": type(self).__name__.lower(), **self.model_dump()}

    @classmethod
    def construct(cls, dict_: dict) -> RoiListModel:
        """Construct an instance from a dictionary."""
        out = cls()
        for roi_dict in dict_["rois"]:
            if not isinstance(roi_dict, dict):
                raise ValueError(f"Expected a dictionary for 'rois', got: {roi_dict!r}")
            roi_type = roi_dict.pop("type")
            roi = ImageRoi.construct(roi_type, roi_dict)
            out.rois.append(roi)
        return out

    def add_roi(self, roi: ImageRoi) -> None:
        """Add a new ROI to the list."""
        self.rois.append(roi)
        if isinstance(roi, ImageRoiND):
            indices = roi.indices
        else:
            indices = ()
        if indices not in self._slice_cache:
            self._slice_cache[indices] = []
        self._slice_cache[indices].append(roi)

    def get_rois_on_slice(self, indices: tuple[int, ...]) -> list[ImageRoi]:
        """Return a list of ROIs on the given slice."""
        indices_to_collect = []
        for i in range(len(indices)):
            indices_to_collect.append(indices[i:])
        out = []
        for idx in indices_to_collect:
            out.extend(self._slice_cache.get(idx, []))
        return out
