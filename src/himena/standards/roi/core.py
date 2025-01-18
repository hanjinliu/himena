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

    def slice_array(self, arr_nd: np.ndarray):
        bb = self.bbox().adjust_to_int("inner")
        arr = arr_nd[..., bb.top : bb.bottom, bb.left : bb.right]
        return arr.reshape(*arr.shape[:-2], arr.shape[-2] * arr.shape[-1])


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

    def length(self) -> float:
        start_x, start_y = self.start
        end_x, end_y = self.end
        return math.hypot(end_x - start_x, end_y - start_y)

    def shifted(self, dx: float, dy: float) -> RotatedRectangleRoi:
        start = (self.start[0] + dx, self.start[1] + dy)
        end = (self.end[0] + dx, self.end[1] + dy)
        return self.model_copy(update={"start": start, "end": end})

    def bbox(self) -> Rect[float]:
        p00, p01, p11, p10 = self._get_vertices()
        xmin = min(p00[0], p01[0], p10[0], p11[0])
        xmax = max(p00[0], p01[0], p10[0], p11[0])
        ymin = min(p00[1], p01[1], p10[1], p11[1])
        ymax = max(p00[1], p01[1], p10[1], p11[1])
        return Rect(xmin, ymin, xmax - xmin, ymax - ymin)

    def _get_vx_vy(self):
        start_x, start_y = self.start
        end_x, end_y = self.end
        length = math.hypot(end_x - start_x, end_y - start_y)
        rad = math.radians(self.angle)
        vx = np.array([math.cos(rad), math.sin(rad)]) * length
        vy = np.array([-math.sin(rad), math.cos(rad)]) * self.width
        return vx, vy

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

    def slice_array(self, arr_nd: np.ndarray):
        bb = self.bbox().adjust_to_int("inner")
        arr = arr_nd[..., bb.top : bb.bottom, bb.left : bb.right]
        _yy, _xx = np.indices(arr.shape[-2:])
        mask = (_yy - self.y) ** 2 / self.height**2 + (
            _xx - self.x
        ) ** 2 / self.width**2 <= 1
        return arr[..., mask]


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

    def to_mask(self, shape: tuple[int, ...]) -> NDArray[np.bool_]:
        arr = np.zeros(shape, dtype=bool)
        arr[..., int(round(self.y)), int(round(self.x))] = True
        return arr

    def slice_array(self, arr_nd: np.ndarray):
        out = _utils.map_coordinates(
            arr_nd, [[self.y], [self.x]], order=1, mode="nearest"
        )
        return out


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

    def slice_array(self, arr_nd: np.ndarray):
        coords = np.stack([self.ys, self.xs], axis=1)
        out = _utils.map_coordinates(arr_nd, coords, order=1, mode="nearest")
        return out


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

    def degree(self) -> float:
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

    def slice_array(self, arr_nd):
        xs, ys = self.arange()
        return _slice_array_along_line(arr_nd, xs, ys)


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
        teval = np.linspace(0, tnots.sum() - rem, num)
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

    def slice_array(self, arr_nd):
        xs, ys = self.arange()
        return _slice_array_along_line(arr_nd, xs, ys)


class PolygonRoi(SegmentedLineRoi):
    """ROI that represents a closed polygon."""

    def to_mask(self, shape: tuple[int, ...]) -> NDArray[np.bool_]:
        return _utils.polygon_mask(shape, np.column_stack((self.ys, self.xs)))


class SplineRoi(Roi2D):
    """ROI that represents a spline curve."""

    degree: int = Field(3, description="Degree of the spline curve.", ge=1)


def _slice_array_along_line(arr_nd: NDArray[np.number], xs, ys):
    coords = np.stack([ys, xs], axis=1)
    out = np.empty(arr_nd.shape[:-2] + (coords.shape[0],), dtype=np.float32)
    for sl in np.ndindex(arr_nd.shape[:-2]):
        arr_2d = arr_nd[sl]
        out[sl] = _utils.map_coordinates(arr_2d, coords, order=1, mode="nearest")
    return out
