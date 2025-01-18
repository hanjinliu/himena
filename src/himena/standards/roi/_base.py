from __future__ import annotations

from functools import cache
from typing import TYPE_CHECKING
from pydantic_compat import BaseModel, Field
from himena.types import Rect
from himena._utils import iter_subclasses

if TYPE_CHECKING:
    from typing import Self
    import numpy as np
    from numpy.typing import NDArray


class RoiModel(BaseModel):
    """Base class for ROIs (Region of Interest) in images."""

    name: str | None = Field(None, description="Name of the ROI.")

    def model_dump_typed(self) -> dict:
        return {
            "type": _strip_roi_suffix(type(self).__name__.lower()),
            **self.model_dump(),
        }

    @classmethod
    def construct(cls, typ: str, dict_: dict) -> RoiModel:
        """Construct an instance from a dictionary."""
        model_type = pick_roi_model(typ)
        return model_type.model_validate(dict_)

    def to_mask(self, shape: tuple[int, ...]) -> NDArray[np.bool_]:
        raise NotImplementedError

    def slice_array(self, arr_nd: np.ndarray) -> np.ndarray:
        mask = self.to_mask(arr_nd.shape)
        return arr_nd[mask]


@cache
def pick_roi_model(typ: str) -> type[RoiModel]:
    for sub in iter_subclasses(RoiModel):
        if _strip_roi_suffix(sub.__name__.lower()) == typ:
            return sub
    raise ValueError(f"Unknown ROI type: {typ!r}")


def _strip_roi_suffix(typ: str) -> str:
    if typ.endswith("roi"):
        typ = typ[:-3]
    return typ


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

    def drop_index(self, ith: int) -> Self | None:
        """Drop the i-th index from the ROI."""
        ind = self.indices[:ith] + self.indices[ith + 1 :]
        return self.model_copy(update={"indices": ind})


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
