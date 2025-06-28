from __future__ import annotations
from typing import Any

from pydantic import Field
from himena.standards.plotting.components import BasePlotModel, Face, Edge
from himena.standards.plotting import models as _m


class Scatter3D(_m.Scatter):
    """Plot model for a 3D scatter plot."""

    z: Any = Field(..., description="Z-axis values.")


class Line3D(_m.Line):
    """Plot model for a 3D line plot."""

    z: Any = Field(..., description="Z-axis values.")


class Surface3D(BasePlotModel):
    """Plot model for a 3D surface plot."""

    x: Any = Field(..., description="X-axis values.")
    y: Any = Field(..., description="Y-axis values.")
    z: Any = Field(..., description="Z-axis values.")
    face: Face = Field(default_factory=Face, description="Properties of the faces.")
    edge: Edge = Field(default_factory=Edge, description="Properties of the edges.")

    def plot_option_dict(self) -> dict[str, Any]:
        from himena.qt.magicgui import EdgePropertyEdit, FacePropertyEdit

        return {
            "name": {"widget_type": "LineEdit", "value": self.name},
            "face": {"widget_type": FacePropertyEdit, "value": self.face.model_dump()},
            "edge": {"widget_type": EdgePropertyEdit, "value": self.edge.model_dump()},
        }


class Mesh3D(BasePlotModel):
    """Plot model for a 3D mesh plot."""

    vertices: Any = Field(..., description="Vertices of the mesh.")
    face_indices: Any = Field(..., description="Face indices of the mesh.")
    face: Face = Field(default_factory=Face, description="Properties of the faces.")
    edge: Edge = Field(default_factory=Edge, description="Properties of the edges.")

    def plot_option_dict(self) -> dict[str, Any]:
        from himena.qt.magicgui import EdgePropertyEdit, FacePropertyEdit

        return {
            "name": {"widget_type": "LineEdit", "value": self.name},
            "face": {"widget_type": FacePropertyEdit, "value": self.face.model_dump()},
            "edge": {"widget_type": EdgePropertyEdit, "value": self.edge.model_dump()},
        }
