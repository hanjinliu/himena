from __future__ import annotations
from typing import Any, Literal

from pydantic_compat import Field
from himena.standards.plotting.components import BasePlotModel, Face, Edge


class Scatter(BasePlotModel):
    """Plot model for scatter plot."""

    x: Any = Field(..., description="X-axis values.")
    y: Any = Field(..., description="Y-axis values.")
    symbol: Any | None = Field(None, description="Symbol of the markers.")
    size: Any | None = Field(None, description="Size of the markers.")
    face: Face = Field(
        default_factory=Face, description="Properties of the marker faces."
    )
    edge: Edge = Field(
        default_factory=Edge, description="Properties of the marker edges."
    )

    def plot_option_dict(self) -> dict[str, Any]:
        from himena.qt._magicgui import EdgePropertyEdit, FacePropertyEdit

        return {
            "name": {"widget_type": "LineEdit", "value": self.name},
            "symbol": {"widget_type": "LineEdit", "value": self.symbol},
            "size": {"annotation": float, "value": self.size},
            "face": {"widget_type": FacePropertyEdit, "value": self.face.model_dump()},
            "edge": {"widget_type": EdgePropertyEdit, "value": self.edge.model_dump()},
        }


class Line(BasePlotModel):
    """Plot model for line plot."""

    x: Any = Field(..., description="X-axis values.")
    y: Any = Field(..., description="Y-axis values.")
    edge: Edge = Field(default_factory=Edge, description="Properties of the line.")
    marker: Scatter | None = Field(None, description="Marker of the line.")

    def plot_option_dict(self) -> dict[str, Any]:
        from himena.qt._magicgui import EdgePropertyEdit

        return {
            "name": {"widget_type": "LineEdit", "value": self.name},
            "edge": {"widget_type": EdgePropertyEdit, "value": self.edge.model_dump()},
        }


class Bar(BasePlotModel):
    """Plot model for bar plot."""

    x: Any = Field(..., description="X-axis values.")
    y: Any = Field(..., description="Y-axis values.")
    bottom: float | Any = Field(0, description="Bottom values of the bars.")
    bar_width: float | None = Field(None, description="Width of the bars.")
    orient: Literal["vertical", "horizontal"] = Field(
        "vertical", description="Orientation of the bar plots."
    )
    face: Face = Field(default_factory=Face, description="Properties of the bars.")
    edge: Edge = Field(default_factory=Edge, description="Properties of the bars.")

    def plot_option_dict(self) -> dict[str, Any]:
        from himena.qt._magicgui import EdgePropertyEdit, FacePropertyEdit

        return {
            "name": {"widget_type": "LineEdit", "value": self.name},
            "bar_width": {"annotation": float, "value": self.bar_width},
            "orient": {"choices": ["vertical", "horizontal"], "value": self.orient},
            "face": {"widget_type": FacePropertyEdit, "value": self.face.model_dump()},
            "edge": {"widget_type": EdgePropertyEdit, "value": self.edge.model_dump()},
        }


class ErrorBar(BasePlotModel):
    """Plot model for error bar plot."""

    x: Any = Field(..., description="X-axis values.")
    y: Any = Field(..., description="Y-axis values.")
    x_error: Any | None = Field(None, description="X-axis error values.")
    y_error: Any | None = Field(None, description="Y-axis error values.")
    capsize: float | None = Field(None, description="Cap size of the error bars.")
    edge: Edge = Field(
        default_factory=Edge, description="Properties of the error bars."
    )

    def plot_option_dict(self) -> dict[str, Any]:
        from himena.qt._magicgui import EdgePropertyEdit

        return {
            "name": {"widget_type": "LineEdit", "value": self.name},
            "capsize": {"annotation": float, "value": self.capsize},
            "edge": {"widget_type": EdgePropertyEdit, "value": self.edge.model_dump()},
        }


class Band(BasePlotModel):
    """Plot model for band plot."""

    x: Any = Field(..., description="X-axis values.")
    y0: Any = Field(..., description="Y-axis values of the lower bound.")
    y1: Any = Field(..., description="Y-axis values of the upper bound.")
    orient: Literal["vertical", "horizontal"] = Field(
        "vertical", description="Orientation of the band fill."
    )
    face: Face = Field(default_factory=Face, description="Properties of the band fill.")
    edge: Edge = Field(default_factory=Edge, description="Properties of the band edge.")

    def plot_option_dict(self) -> dict[str, Any]:
        from himena.qt._magicgui import EdgePropertyEdit, FacePropertyEdit

        return {
            "name": {"widget_type": "LineEdit", "value": self.name},
            "orient": {"choices": ["vertical", "horizontal"], "value": self.orient},
            "face": {"widget_type": FacePropertyEdit, "value": self.face.model_dump()},
            "edge": {"widget_type": EdgePropertyEdit, "value": self.edge.model_dump()},
        }


class Histogram(BasePlotModel):
    """Plot model for a histogram."""

    data: Any = Field(..., description="Data values.")
    bins: int = Field(10, description="Number of bins.")
    range: tuple[float, float] | None = Field(
        None, description="Range of the histogram."
    )
    orient: Literal["vertical", "horizontal"] = Field(
        "vertical", description="Orientation of the histogram."
    )
    stat: Literal["count", "density", "probability"] = Field(
        "count", description="Statistic of the histogram."
    )
    face: Face = Field(
        default_factory=Face, description="Properties of the histogram face."
    )
    edge: Edge = Field(
        default_factory=Edge, description="Properties of the histogram edge."
    )

    def plot_option_dict(self) -> dict[str, Any]:
        from himena.qt._magicgui import (
            EdgePropertyEdit,
            FacePropertyEdit,
            FloatListEdit,
        )

        return {
            "name": {"widget_type": "LineEdit", "value": self.name},
            "bins": {"annotation": int, "value": self.bins},
            "range": {
                "widget_type": FloatListEdit,
                "value": self.range,
                "nullable": True,
            },
            "orient": {"choices": ["vertical", "horizontal"], "value": self.orient},
            "stat": {
                "choices": ["count", "density", "probability"],
                "value": self.stat,
            },
            "face": {"widget_type": FacePropertyEdit, "value": self.face.model_dump()},
            "edge": {"widget_type": EdgePropertyEdit, "value": self.edge.model_dump()},
        }
