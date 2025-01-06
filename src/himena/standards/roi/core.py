from __future__ import annotations

from functools import cache
import math
from typing import TYPE_CHECKING, Any, Iterator, Union
import numpy as np
from pydantic import field_serializer
from pydantic_compat import BaseModel, Field, field_validator
from himena.types import Rect

if TYPE_CHECKING:
    from numpy.typing import NDArray
    from typing import Self


class RoiModel(BaseModel):
    """Base class for ROIs (Region of Interest) in images."""

    name: str | None = Field(None, description="Name of the ROI.")

    def model_dump_typed(self) -> dict:
        typ = type(self).__name__.lower()
        if typ.endswith("roi"):
            typ = typ[:-3]
        return {"type": typ, **self.model_dump()}

    @classmethod
    def construct(cls, typ: str, dict_: dict) -> RoiModel:
        """Construct an instance from a dictionary."""
        model_type = _pick_roi_model(typ)
        return model_type.model_validate(dict_)


@cache
def _pick_roi_model(typ: str) -> type[RoiModel]:
    for sub in RoiModel.__subclasses__():
        if sub.__name__.lower() == typ:
            return sub
    raise ValueError(f"Unknown ROI type: {typ!r}")


def default_roi_label(nth: int) -> str:
    """Return a default label for the n-th ROI."""
    return f"ROI-{nth}"


class RoiND(RoiModel):
    indices: tuple[int, ...] = Field(
        default=(), description="Indices of the ROI in the >nD dimensions."
    )

    def flattened(self) -> Self:
        """Return a copy of the ROI with indices flattened."""
        return self.model_copy(update={"indices": ()})


class Roi1D(RoiND):
    def shifted(self, dx: float, dy: float) -> Self:
        """Return a new 1D ROI translated by the given amount."""
        raise NotImplementedError


class Roi2D(RoiND):
    def bbox(self) -> Rect[float]:
        """Return the bounding box of the ROI."""
        raise NotImplementedError

    def shifted(self, dx: float, dy: float) -> Self:
        """Return a new 2D ROI translated by the given amount."""
        raise NotImplementedError


class Roi3D(RoiND):
    def shifted(self, dx: float, dy: float, dz: float) -> Self:
        """Return a new 3D ROI translated by the given amount."""
        raise NotImplementedError


class SpanRoi(Roi1D):
    """ROI that represents a span in 1D space."""

    start: float = Field(..., description="Start of the span.")
    end: float = Field(..., description="End of the span.")

    def shifted(self, dx: float, dy: float) -> SpanRoi:
        return SpanRoi(start=self.start + dx, end=self.end + dy)

    def width(self) -> float:
        return self.end - self.start


class PointRoi1D(Roi1D):
    """ROI that represents a point in 1D space."""

    x: float = Field(..., description="X-coordinate of the point.")

    def shifted(self, dx: float, dy: float) -> PointRoi1D:
        return PointRoi1D(x=self.x + dx)


class PointsRoi1D(Roi1D):
    """ROI that represents a set of points in 1D space."""

    xs: Any = Field(..., description="List of x-coordinates.")

    @field_validator("xs")
    def _validate_np_array(cls, v) -> NDArray[np.number]:
        out = np.asarray(v)
        if out.dtype.kind not in "if":
            raise ValueError("Must be a numerical array.")
        return out

    def shifted(self, dx: float, dy: float) -> PointsRoi1D:
        return PointsRoi1D(xs=self.xs + dx)


class RectangleRoi(Roi2D):
    """ROI that represents a rectangle."""

    x: Union[int, float] = Field(
        ..., description="X-coordinate of the top-left corner."
    )
    y: Union[int, float] = Field(
        ..., description="Y-coordinate of the top-left corner."
    )
    width: Union[int, float] = Field(..., description="Width of the rectangle.")
    height: Union[int, float] = Field(..., description="Height of the rectangle.")

    def shifted(self, dx: float, dy: float) -> RectangleRoi:
        """Return a new rectangle shifted by the given amount."""
        return self.model_copy(update={"x": self.x + dx, "y": self.y + dy})

    def area(self) -> float:
        return self.width * self.height

    def bbox(self) -> Rect[float]:
        return Rect(self.x, self.y, self.width, self.height)


class RotatedRoi2D(Roi2D):
    angle: float = Field(..., description="Counter-clockwise angle in degrees.")


class RotatedRectangleRoi(RotatedRoi2D):
    """ROI that represents a rotated rectangle.

    Attribute `angle` is defined by the counter-clockwise rotation around the center of
    the rectangle.
    """

    start: tuple[float, float] = Field(..., description="X-coordinate of the center.")
    end: tuple[float, float] = Field(..., description="Y-coordinate of the center.")
    width: float = Field(..., description="Width of the rectangle.")

    def shifted(self, dx: float, dy: float) -> RotatedRectangleRoi:
        start = (self.start[0] + dx, self.start[1] + dy)
        end = (self.end[0] + dx, self.end[1] + dy)
        return self.model_copy(update={"start": start, "end": end})

    def bbox(self) -> Rect[float]:
        start_x, start_y = self.start
        end_x, end_y = self.end
        length = math.hypot(end_x - start_x, end_y - start_y)
        rad = math.radians(self.angle)
        vx = np.array([math.cos(rad), math.sin(rad)]) * length
        vy = np.array([-math.sin(rad), math.cos(rad)]) * self.width
        center = np.array([start_x + end_x, start_y + end_y]) / 2
        p00 = center - vx / 2 - vy / 2
        p01 = center - vx / 2 + vy / 2
        p10 = center + vx / 2 - vy / 2
        p11 = center + vx / 2 + vy / 2
        xmin = min(p00[0], p01[0], p10[0], p11[0])
        xmax = max(p00[0], p01[0], p10[0], p11[0])
        ymin = min(p00[1], p01[1], p10[1], p11[1])
        ymax = max(p00[1], p01[1], p10[1], p11[1])
        return Rect(xmin, ymin, xmax - xmin, ymax - ymin)


class EllipseRoi(Roi2D):
    """ROI that represents an ellipse."""

    x: Union[int, float] = Field(..., description="X-coordinate of the center.")
    y: Union[int, float] = Field(..., description="Y-coordinate of the center.")
    width: Union[int, float] = Field(..., description="Diameter along the x-axis.")
    height: Union[int, float] = Field(..., description="Diameter along the y-axis.")

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


class PointRoi2D(Roi2D):
    """ROI that represents a single point."""

    x: float = Field(..., description="X-coordinate of the point.")
    y: float = Field(..., description="Y-coordinate of the point.")

    def shifted(self, dx: float, dy: float) -> PointRoi2D:
        return self.model_copy(update={"x": self.x + dx, "y": self.y + dy})

    def bbox(self) -> Rect[float]:
        return Rect(self.x, self.y, 0, 0)


class PointsRoi2D(Roi2D):
    """ROI that represents a set of points."""

    xs: Any = Field(..., description="List of x-coordinates.")
    ys: Any = Field(..., description="List of y-coordinates.")

    @field_validator("xs", "ys")
    def _validate_np_arrays(cls, v) -> NDArray[np.number]:
        out = np.asarray(v)
        if out.dtype.kind not in "if":
            raise ValueError("Must be a numerical array.")
        return out

    def shifted(self, dx: float, dy: float) -> PointsRoi2D:
        return self.model_copy(update={"xs": self.xs + dx, "ys": self.ys + dy})

    def bbox(self) -> Rect[float]:
        xmin, xmax = np.min(self.xs), np.max(self.xs)
        ymin, ymax = np.min(self.ys), np.max(self.ys)
        return Rect(xmin, ymin, xmax - xmin, ymax - ymin)


class SegmentedLineRoi(PointsRoi2D):
    """ROI that represents a segmented line."""

    def length(self) -> float:
        return np.sum(np.hypot(np.diff(self.xs), np.diff(self.ys)))


class PolygonRoi(SegmentedLineRoi):
    """ROI that represents a closed polygon."""


class SplineRoi(Roi2D):
    """ROI that represents a spline curve."""

    degree: int = Field(3, description="Degree of the spline curve.", ge=1)


class LineRoi(Roi2D):
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

    rois: list[RoiModel] = Field(default_factory=list, description="List of ROIs.")

    def model_dump_typed(self) -> dict:
        return {"type": type(self).__name__.lower(), **self.model_dump()}

    @field_serializer("rois")
    def _serialize_rois(self, v: list[RoiModel]) -> list[dict]:
        return [roi.model_dump_typed() for roi in v]

    @classmethod
    def construct(cls, dict_: dict) -> RoiListModel:
        """Construct an instance from a dictionary."""
        out = cls()
        for roi_dict in dict_["rois"]:
            if not isinstance(roi_dict, dict):
                raise ValueError(f"Expected a dictionary for 'rois', got: {roi_dict!r}")
            roi_type = roi_dict.pop("type")
            roi = RoiModel.construct(roi_type, roi_dict)
            out.rois.append(roi)
        return out

    def __getitem__(self, key: int) -> RoiModel:
        return self.rois[key]

    def __iter__(self) -> Iterator[RoiModel]:
        return iter(self.rois)

    def __len__(self) -> int:
        return len(self.rois)
