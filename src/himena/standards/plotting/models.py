from __future__ import annotations
from typing import Any, Literal

from pydantic_compat import Field
from himena.standards.plotting.components import BasePlotModel, Face, Edge


class PlotModelXY(BasePlotModel):
    x: Any = Field(..., description="X-axis values.")
    y: Any = Field(..., description="Y-axis values.")


class Scatter(PlotModelXY):
    """Plot model for scatter plot."""

    symbol: Any | None = Field(None, description="Symbol of the markers.")
    size: Any | None = Field(None, description="Size of the markers.")
    face: Face = Field(
        default_factory=Face, description="Properties of the marker faces."
    )
    edge: Edge = Field(
        default_factory=Edge, description="Properties of the marker edges."
    )

    def plot_option_dict(self) -> dict[str, Any]:
        from himena.qt.magicgui import EdgePropertyEdit, FacePropertyEdit

        return {
            "name": {"widget_type": "LineEdit", "value": self.name},
            "symbol": {"widget_type": "LineEdit", "value": self.symbol},
            "size": {"annotation": float, "value": self.size},
            "face": {"widget_type": FacePropertyEdit, "value": self.face.model_dump()},
            "edge": {"widget_type": EdgePropertyEdit, "value": self.edge.model_dump()},
        }


class Line(PlotModelXY):
    """Plot model for line plot."""

    edge: Edge = Field(default_factory=Edge, description="Properties of the line.")
    marker: Scatter | None = Field(None, description="Marker of the line.")

    def plot_option_dict(self) -> dict[str, Any]:
        from himena.qt.magicgui import EdgePropertyEdit

        return {
            "name": {"widget_type": "LineEdit", "value": self.name},
            "edge": {"widget_type": EdgePropertyEdit, "value": self.edge.model_dump()},
        }


class Bar(PlotModelXY):
    """Plot model for bar plot."""

    bottom: float | Any = Field(0, description="Bottom values of the bars.")
    bar_width: float | None = Field(None, description="Width of the bars.")
    orient: Literal["vertical", "horizontal"] = Field(
        "vertical", description="Orientation of the bar plots."
    )
    face: Face = Field(default_factory=Face, description="Properties of the bars.")
    edge: Edge = Field(default_factory=Edge, description="Properties of the bars.")

    def plot_option_dict(self) -> dict[str, Any]:
        from himena.qt.magicgui import EdgePropertyEdit, FacePropertyEdit

        return {
            "name": {"widget_type": "LineEdit", "value": self.name},
            "bar_width": {"annotation": float, "value": self.bar_width},
            "orient": {"choices": ["vertical", "horizontal"], "value": self.orient},
            "face": {"widget_type": FacePropertyEdit, "value": self.face.model_dump()},
            "edge": {"widget_type": EdgePropertyEdit, "value": self.edge.model_dump()},
        }


class ErrorBar(PlotModelXY):
    """Plot model for error bar plot."""

    x_error: Any | None = Field(None, description="X-axis error values.")
    y_error: Any | None = Field(None, description="Y-axis error values.")
    capsize: float | None = Field(None, description="Cap size of the error bars.")
    edge: Edge = Field(
        default_factory=Edge, description="Properties of the error bars."
    )

    def plot_option_dict(self) -> dict[str, Any]:
        from himena.qt.magicgui import EdgePropertyEdit

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
        from himena.qt.magicgui import EdgePropertyEdit, FacePropertyEdit

        return {
            "name": {"widget_type": "LineEdit", "value": self.name},
            "orient": {"choices": ["vertical", "horizontal"], "value": self.orient},
            "face": {"widget_type": FacePropertyEdit, "value": self.face.model_dump()},
            "edge": {"widget_type": EdgePropertyEdit, "value": self.edge.model_dump()},
        }


class Span(BasePlotModel):
    """Plot model for span plot."""

    start: float = Field(..., description="Starting value of the lower bound.")
    end: float = Field(..., description="Ending value of the upper bound.")
    orient: Literal["vertical", "horizontal"] = Field(
        "vertical",
        description="Orientation of the span. 'vertical' means the span"
        "is vertically unlimited.",
    )
    face: Face = Field(default_factory=Face, description="Properties of the span fill.")
    edge: Edge = Field(default_factory=Edge, description="Properties of the span edge.")

    def plot_option_dict(self) -> dict[str, Any]:
        from himena.qt.magicgui import EdgePropertyEdit, FacePropertyEdit

        return {
            "name": {"widget_type": "LineEdit", "value": self.name},
            "x0": {"annotation": float, "value": self.start},
            "x1": {"annotation": float, "value": self.end},
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
        from himena.qt.magicgui import (
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


ANCHOR_STRINGS = Literal[
    "center", "left", "right", "top", "bottom", "top_left", "top_right",
    "bottom_left", "bottom_right"
]  # fmt: skip


class Texts(PlotModelXY):
    """Plot model for texts."""

    texts: Any = Field(..., description="Texts to be displayed.")
    size: int = Field(12, description="Font size of the texts.")
    color: str = Field("black", description="Font color of the texts.")
    family: str = Field("Arial", description="Font family of the texts.")
    anchor: ANCHOR_STRINGS = Field(
        "center",
        description="Anchor position of the texts. 'center' means the center of the text.",
    )
    rotation: float = Field(0, description="Rotation angle of the texts.")

    def plot_option_dict(self) -> dict[str, Any]:
        return {
            "name": {"widget_type": "LineEdit", "value": self.name},
            "font_size": {"annotation": int, "value": self.size},
            "font_color": {"annotation": str, "value": self.color},
            "font_family": {"annotation": str, "value": self.family},
        }
