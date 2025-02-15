from typing import Sequence, TYPE_CHECKING

import numpy as np
from pydantic_compat import Field
from himena.standards.plotting.layout import BaseLayoutModel
from himena.standards.plotting.components import (
    Axis,
    AxesBase,
    parse_edge,
    parse_face_edge,
)
from himena.standards.plotting import models3d as _m3d

if TYPE_CHECKING:
    from numpy.typing import NDArray


class Axes3D(AxesBase):
    """Layout model for 3D axes."""

    x: Axis = Field(default_factory=Axis, description="X-axis settings.")
    y: Axis = Field(default_factory=Axis, description="Y-axis settings.")
    z: Axis = Field(default_factory=Axis, description="Z-axis settings.")

    def scatter(
        self,
        x: Sequence[float],
        y: Sequence[float],
        z: Sequence[float],
        *,
        symbol: str = "o",
        size: float | None = None,
        **kwargs,
    ) -> _m3d.Scatter3D:
        """Create a 3D scatter plot."""
        model = _m3d.Scatter3D(
            x=x, y=y, z=z, symbol=symbol, size=size, **parse_face_edge(kwargs)
        )
        self.models.append(model)
        return model

    def plot(
        self,
        x: Sequence[float],
        y: Sequence[float],
        z: Sequence[float],
        **kwargs,
    ) -> _m3d.Line3D:
        """Create a 3D line plot."""
        model = _m3d.Line3D(x=x, y=y, z=z, **parse_edge(kwargs))
        self.models.append(model)
        return model

    def surface(
        self,
        x: "NDArray[np.number]",
        y: "NDArray[np.number]",
        z: "NDArray[np.number]",
        **kwargs,
    ) -> _m3d.Surface3D:
        """Create a 3D surface plot."""
        model = _m3d.Surface3D(x=x, y=y, z=z, **parse_face_edge(kwargs))
        self.models.append(model)
        return model

    def mesh(
        self,
        vertices: "NDArray[np.number]",
        face_indices: "NDArray[np.number]",
        **kwargs,
    ) -> _m3d.Mesh3D:
        """Create a 3D mesh plot."""
        model = _m3d.Mesh3D(
            vertices=vertices, face_indices=face_indices, **parse_face_edge(kwargs)
        )
        self.models.append(model)
        return model


class SingleAxes3D(BaseLayoutModel):
    axes: Axes3D = Field(default_factory=Axes3D, description="Child 3D axes.")
