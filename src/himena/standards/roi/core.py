from __future__ import annotations

import math
from typing import Any, Union
import numpy as np
from numpy.typing import NDArray
from pydantic_compat import Field, field_validator
from himena.types import Rect
from himena.standards.roi._base import Roi1D, Roi2D
from himena.standards.roi import _utils


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
        """Return the area of the rectangle."""
        return self.width * self.height

    def bbox(self) -> Rect[float]:
        """Return the bounding box of the rectangle."""
        return Rect(self.x, self.y, self.width, self.height)

    def to_mask(self, shape: tuple[int, ...]) -> NDArray[np.bool_]:
        bb = self.bbox().adjust_to_int("inner")
        arr = np.zeros(shape, dtype=bool)
        arr[..., bb.top : bb.bottom, bb.left : bb.right] = True
        return arr


class RotatedRoi2D(Roi2D):
    start: tuple[float, float] = Field(
        ..., description="Coordinate of the start point."
    )
    end: tuple[float, float] = Field(..., description="Coordinate of the end point.")
    width: float = Field(..., description="Width of the ROI.")

    def length(self) -> float:
        start_x, start_y = self.start
        end_x, end_y = self.end
        return math.hypot(end_x - start_x, end_y - start_y)

    def shifted(self, dx: float, dy: float) -> RotatedRectangleRoi:
        start = (self.start[0] + dx, self.start[1] + dy)
        end = (self.end[0] + dx, self.end[1] + dy)
        return self.model_copy(update={"start": start, "end": end})

    def _get_vx_vy(self):
        start_x, start_y = self.start
        end_x, end_y = self.end
        length = math.hypot(end_x - start_x, end_y - start_y)
        rad = self.angle_radian()
        vx = np.array([math.cos(rad), math.sin(rad)]) * length
        vy = np.array([-math.sin(rad), math.cos(rad)]) * self.width
        return vx, vy

    def angle(self) -> float:
        """Counter-clockwise rotation."""
        return math.degrees(self.angle_radian())

    def angle_radian(self) -> float:
        return math.atan2(self.end[1] - self.start[1], self.end[0] - self.start[0])


class RotatedRectangleRoi(RotatedRoi2D):
    """ROI that represents a rotated rectangle."""

    def area(self) -> float:
        return self.length() * self.width

    def bbox(self) -> Rect[float]:
        p00, p01, p11, p10 = self._get_vertices()
        xmin = min(p00[0], p01[0], p10[0], p11[0])
        xmax = max(p00[0], p01[0], p10[0], p11[0])
        ymin = min(p00[1], p01[1], p10[1], p11[1])
        ymax = max(p00[1], p01[1], p10[1], p11[1])
        return Rect(xmin, ymin, xmax - xmin, ymax - ymin)

    def _get_vertices(self):
        start_x, start_y = self.start
        end_x, end_y = self.end
        vx, vy = self._get_vx_vy()
        center = np.array([start_x + end_x, start_y + end_y]) / 2
        p00 = center - vx / 2 - vy / 2
        p01 = center - vx / 2 + vy / 2
        p10 = center + vx / 2 - vy / 2
        p11 = center + vx / 2 + vy / 2
        return p00, p01, p11, p10

    def to_mask(self, shape: tuple[int, ...]):
        vertices = np.stack(self._get_vertices(), axis=0)
        return _utils.polygon_mask(shape, vertices[:, ::-1])


class EllipseRoi(Roi2D):
    """ROI that represents an ellipse."""

    x: Union[int, float] = Field(..., description="X-coordinate of the center.")
    y: Union[int, float] = Field(..., description="Y-coordinate of the center.")
    width: Union[int, float] = Field(..., description="Diameter along the x-axis.")
    height: Union[int, float] = Field(..., description="Diameter along the y-axis.")

    def center(self) -> tuple[float, float]:
        return self.x + self.width / 2, self.y + self.height / 2

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

    def to_mask(self, shape: tuple[int, ...]) -> NDArray[np.bool_]:
        _yy, _xx = np.indices(shape[-2:])
        cx, cy = self.center()
        comp_a = (_yy - cy) / self.height * 2
        comp_b = (_xx - cx) / self.width * 2
        return comp_a**2 + comp_b**2 <= 1


class RotatedEllipseRoi(RotatedRoi2D):
    """ROI that represents a rotated ellipse."""

    def area(self) -> float:
        return self.length() * self.width * math.pi / 4

    def to_mask(self, shape: tuple[int, ...]) -> NDArray[np.bool_]:
        _yy, _xx = np.indices(shape[-2:])
        start_x, start_y = self.start
        end_x, end_y = self.end
        length = math.hypot(end_x - start_x, end_y - start_y)
        cx, cy = (start_x + end_x) / 2, (start_y + end_y) / 2
        angle = self.angle_radian()
        comp_a = (_yy - cy) / length * 2
        comp_b = (_xx - cx) / self.width * 2
        comp_a, comp_b = (
            comp_a * math.cos(angle) - comp_b * math.sin(angle),
            comp_a * math.sin(angle) + comp_b * math.cos(angle),
        )
        return comp_a**2 + comp_b**2 <= 1


class PointRoi2D(Roi2D):
    """ROI that represents a single point."""

    x: float = Field(..., description="X-coordinate of the point.")
    y: float = Field(..., description="Y-coordinate of the point.")

    def shifted(self, dx: float, dy: float) -> PointRoi2D:
        return self.model_copy(update={"x": self.x + dx, "y": self.y + dy})

    def bbox(self) -> Rect[float]:
        return Rect(self.x, self.y, 0, 0)

    def to_mask(self, shape: tuple[int, ...]) -> NDArray[np.bool_]:
        arr = np.zeros(shape, dtype=bool)
        arr[..., int(round(self.y)), int(round(self.x))] = True
        return arr


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

    def to_mask(self, shape: tuple[int, ...]) -> NDArray[np.bool_]:
        arr = np.zeros(shape, dtype=bool)
        xs = np.asarray(self.xs).round().astype(int)
        ys = np.asarray(self.ys).round().astype(int)
        arr[..., ys, xs] = True
        return arr


class LineRoi(Roi2D):
    """A 2D line ROI."""

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

    def angle(self) -> float:
        """Angle in degrees."""
        return math.degrees(math.atan2(self.y2 - self.y1, self.x2 - self.x1))

    def radian(self) -> float:
        """Angle in radians."""
        return math.atan2(self.y2 - self.y1, self.x2 - self.x1)

    def linspace(self, num: int) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
        """Return a tuple of x and y coordinates of np.linspace along the line."""
        return np.linspace(self.x1, self.x2, num), np.linspace(self.y1, self.y2, num)

    def arange(
        self, step: float = 1.0
    ) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
        """Return a tuple of x and y coordinates of np.arange along the line."""
        radian = self.radian()
        num, rem = divmod(self.length(), step)
        xrem = rem * math.cos(radian)
        yrem = rem * math.sin(radian)
        return (
            np.linspace(self.x1, self.x2 - xrem, int(num) + 1),
            np.linspace(self.y1, self.y2 - yrem, int(num) + 1),
        )

    def bbox(self) -> Rect[float]:
        xmin, xmax = min(self.x1, self.x2), max(self.x1, self.x2)
        ymin, ymax = min(self.y1, self.y2), max(self.y1, self.y2)
        return Rect(xmin, ymin, xmax - xmin, ymax - ymin)

    def to_mask(self, shape: tuple[int, ...]) -> NDArray[np.bool_]:
        arr = np.zeros(shape, dtype=bool)
        xs, ys = self.linspace(int(math.ceil(self.length())))
        xs = xs.round().astype(int)
        ys = ys.round().astype(int)
        arr[ys, xs] = True
        return arr


class SegmentedLineRoi(PointsRoi2D):
    """ROI that represents a segmented line."""

    def length(self) -> np.float64:
        return np.sum(self.lengths())

    def lengths(self) -> NDArray[np.float64]:
        return np.hypot(np.diff(self.xs), np.diff(self.ys))

    def linspace(self, num: int) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
        """Return a tuple of x and y coordinates of np.linspace along the line."""
        tnots = np.concatenate([[0], self.lengths()], dtype=np.float64)
        teval = np.linspace(0, tnots.sum(), num)
        xi = np.interp(teval, tnots, self.xs)
        yi = np.interp(teval, tnots, self.ys)
        return xi, yi

    def arange(
        self, step: float = 1.0
    ) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
        tnots = np.concatenate([[0], self.lengths()], dtype=np.float64)
        length = tnots.sum()
        num, rem = divmod(length, step)
        teval = np.linspace(0, tnots.sum() - rem, int(round(num)))
        xi = np.interp(teval, tnots, self.xs)
        yi = np.interp(teval, tnots, self.ys)
        return xi, yi

    def to_mask(self, shape: tuple[int, ...]) -> NDArray[np.bool_]:
        arr = np.zeros(shape, dtype=bool)
        xs, ys = self.linspace(int(math.ceil(self.length())))
        xs = xs.round().astype(int)
        ys = ys.round().astype(int)
        arr[ys, xs] = True
        return arr


class PolygonRoi(SegmentedLineRoi):
    """ROI that represents a closed polygon."""

    def to_mask(self, shape: tuple[int, ...]) -> NDArray[np.bool_]:
        return _utils.polygon_mask(shape, np.column_stack((self.ys, self.xs)))

    def area(self) -> float:
        dot_xy = np.dot(self.xs, np.roll(self.ys, 1))
        dot_yx = np.dot(self.ys, np.roll(self.xs, 1))
        return np.abs(dot_xy - dot_yx) / 2


class SplineRoi(Roi2D):
    """ROI that represents a spline curve."""

    degree: int = Field(3, description="Degree of the spline curve.", ge=1)
