from __future__ import annotations

from typing import Iterator
from pydantic import field_serializer
from pydantic_compat import BaseModel, Field
from himena.standards.roi._base import RoiModel, RoiND


class RoiListModel(BaseModel):
    """List of ROIs, with useful methods."""

    rois: list[RoiModel] = Field(default_factory=list, description="List of ROIs.")
    axis_names: list[str] = Field(
        default_factory=list, description="Names of the axes in the >nD dimensions."
    )

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

    def take_axis(self, axis: str, index: int):
        idx = self.axis_names.index(axis)
        rois = []
        for _roi in self:
            if isinstance(_roi, RoiND):
                if len(_roi.indices) <= idx or _roi.indices[idx] != index:
                    continue
                else:
                    _roi_new = _roi.drop_index(idx)
            else:
                _roi_new = _roi
            rois.append(_roi_new)
        return RoiListModel(
            rois=rois,
            axis_names=self.axis_names[:idx] + self.axis_names[idx + 1 :],
        )

    def project(self, axis: str):
        idx = self.axis_names.index(axis)
        rois = []
        for _roi in self:
            if isinstance(_roi, RoiND):
                if len(_roi.indices) <= idx:
                    continue
                else:
                    _roi_new = _roi.drop_index(idx)
            else:
                _roi_new = _roi
            rois.append(_roi_new)
        return RoiListModel(
            rois=rois,
            axis_names=self.axis_names[:idx] + self.axis_names[idx + 1 :],
        )
