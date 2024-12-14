from __future__ import annotations
from typing import Any, Literal

from pydantic_compat import BaseModel, Field, field_validator

from himena.consts import PYDANTIC_CONFIG_STRICT


class BasePlotModel(BaseModel):
    model_config = PYDANTIC_CONFIG_STRICT
    name: str = Field(default="", description="Name of the plot.")

    @staticmethod
    def construct(type: str, dict_: dict[str, Any]) -> BasePlotModel:
        if type == "scatter":
            return Scatter(**dict_)
        if type == "line":
            return Line(**dict_)
        if type == "bar":
            return Bar(**dict_)
        if type == "errorbar":
            return ErrorBar(**dict_)
        if type == "band":
            return Band(**dict_)
        if type == "histogram":
            return Histogram(**dict_)
        raise ValueError(f"Unknown plot type: {type!r}")

    @field_validator("name", mode="before")
    def _validate_name(cls, name: str) -> str:
        if name is None:
            return ""
        return name

    def model_dump_typed(self) -> dict[str, Any]:
        return {"type": type(self).__name__.lower(), **self.model_dump()}

    def plot_option_dict(self) -> dict[str, Any]:
        """Return the GUI option dict for this plot for editing."""
        return {"name": {"widget_type": "LineEdit", "value": self.name}}


class Face(BaseModel):
    color: Any | None = Field(None, description="Color of the face.")
    hatch: Any | None = Field(None, description="Hatch pattern of the face.")


class Edge(BaseModel):
    color: Any | None = Field(None, description="Color of the edge.")
    width: float | None = Field(None, description="Width of the edge.")
    style: Any | None = Field(None, description="Style of the edge.")


def parse_edge(kwargs: dict[str, Any]) -> dict:
    color = kwargs.pop("color", kwargs.pop("edge_color", None))
    width = kwargs.pop("width", kwargs.pop("edge_width", None))
    style = kwargs.pop("style", kwargs.pop("edge_style", None))
    name = kwargs.pop("name", None)
    if kwargs:
        raise ValueError(f"Extra keyword arguments: {list(kwargs.keys())!r}")
    edge = Edge(color=color, width=width, style=style)
    return {"edge": edge, "name": name}


def parse_face_edge(kwargs: dict[str, Any]) -> dict:
    color = kwargs.pop("color", kwargs.pop("face_color", None))
    hatch = kwargs.pop("hatch", kwargs.pop("face_hatch", None))
    kwargs = parse_edge(kwargs)
    if kwargs.get("color") is None:
        kwargs["color"] = color
    face = Face(color=color, hatch=hatch)
    return {"face": face, **kwargs}


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
    data: Any = Field(..., description="Data values.")
    bins: int = Field(10, description="Number of bins.")
    range: tuple[float, float] | None = Field(
        None, description="Range of the histogram."
    )
    orient: Literal["vertical", "horizontal"] = Field(
        "vertical", description="Orientation of the histogram."
    )
    face: Face = Field(
        default_factory=Face, description="Properties of the histogram face."
    )
    edge: Edge = Field(
        default_factory=Edge, description="Properties of the histogram edge."
    )

    def plot_option_dict(self) -> dict[str, Any]:
        from himena.qt._magicgui import EdgePropertyEdit, FacePropertyEdit

        return {
            "name": {"widget_type": "LineEdit", "value": self.name},
            "bins": {"annotation": int, "value": self.bins},
            "range": {"annotation": tuple[float, float], "value": self.range},
            "orient": {"choices": ["vertical", "horizontal"], "value": self.orient},
            "face": {"widget_type": FacePropertyEdit, "value": self.face.model_dump()},
            "edge": {"widget_type": EdgePropertyEdit, "value": self.edge.model_dump()},
        }
