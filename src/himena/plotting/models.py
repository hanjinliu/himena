from __future__ import annotations
from typing import Any, Literal, Sequence

from pydantic_compat import BaseModel, Field


class BasePlotModel(BaseModel):
    pass


class Scatter(BasePlotModel):
    """Plot model for scatter plot."""

    x: Sequence[float] = Field(..., description="X-axis values.")
    y: Sequence[float] = Field(..., description="Y-axis values.")
    symbol: Any | None = Field(None, description="Symbol of the markers.")
    size: float | Sequence[float] | None = Field(
        None, description="Size of the markers."
    )
    color: Any | None = Field(None, description="Color of the markers.")
    hatch: Any | None = Field(None, description="Hatch pattern of the markers.")
    edge_color: Any | None = Field(None, description="Edge color of the markers.")
    edge_width: float | None = Field(None, description="Edge width of the markers.")
    edge_style: Any | None = Field(None, description="Edge style of the markers.")


class Line(BasePlotModel):
    x: Sequence[float] = Field(..., description="X-axis values.")
    y: Sequence[float] = Field(..., description="Y-axis values.")
    color: Any | None = Field(None, description="Color of the line.")
    width: float | None = Field(None, description="Width of the line.")
    style: Any | None = Field(None, description="Style of the line.")
    marker: Scatter | None = Field(None, description="Marker of the line.")


class Bar(BasePlotModel):
    x: Sequence[float] = Field(..., description="X-axis values.")
    y: Sequence[float] = Field(..., description="Y-axis values.")
    bottom: float | Sequence[float] = Field(0, description="Bottom values of the bars.")
    color: Any | None = Field(None, description="Color of the bars.")
    hatch: Any | None = Field(None, description="Hatch pattern of the bars.")
    edge_color: Any | None = Field(None, description="Edge color of the bars.")
    edge_width: float | None = Field(None, description="Edge width of the bars.")
    edge_style: Any | None = Field(None, description="Edge style of the bars.")


class ErrorBar(BasePlotModel):
    x: Sequence[float] = Field(..., description="X-axis values.")
    y: Sequence[float] = Field(..., description="Y-axis values.")
    x_error: Sequence[float] | None = Field(None, description="X-axis error values.")
    y_error: Sequence[float] | None = Field(None, description="Y-axis error values.")
    capsize: float | None = Field(None, description="Cap size of the error bars.")
    color: Any | None = Field(None, description="Color of the error bars.")
    hatch: Any | None = Field(None, description="Hatch pattern of the error bars.")
    edge_color: Any | None = Field(None, description="Edge color of the error bars.")
    edge_width: float | None = Field(None, description="Edge width of the error bars.")
    edge_style: Any | None = Field(None, description="Edge style of the error bars.")


class Histogram(BasePlotModel):
    data: Sequence[float] = Field(..., description="Data values.")
    bins: int = Field(10, description="Number of bins.")
    range: tuple[float, float] | None = Field(
        None, description="Range of the histogram."
    )
    orient: Literal["vertical", "horizontal"] = Field(
        "vertical", description="Orientation of the histogram."
    )
    color: Any | None = Field(None, description="Color of the histogram.")
    hatch: Any | None = Field(None, description="Hatch pattern of the histogram.")
    edge_color: Any | None = Field(None, description="Edge color of the histogram.")
    edge_width: float | None = Field(None, description="Edge width of the histogram.")
    edge_style: Any | None = Field(None, description="Edge style of the histogram.")
