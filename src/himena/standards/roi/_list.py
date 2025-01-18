from __future__ import annotations
import json

import numpy as np
from himena.standards.roi._base import RoiModel
from himena.utils.ndobject import NDObjectCollection


class RoiListModel(NDObjectCollection[RoiModel]):
    """List of ROIs, with useful methods."""

    def model_dump_typed(self) -> dict:
        return {
            "rois": [roi.model_dump_typed() for roi in self],
            "indices": self.indices.tolist() if self.indices is not None else None,
            "axis_names": self.axis_names,
        }

    @classmethod
    def construct(cls, dict_: dict) -> RoiListModel:
        """Construct an instance from a dictionary."""
        rois = []
        for roi_dict in dict_["rois"]:
            if not isinstance(roi_dict, dict):
                raise ValueError(f"Expected a dictionary for 'rois', got: {roi_dict!r}")
            roi_type = roi_dict.pop("type")
            roi = RoiModel.construct(roi_type, roi_dict)
            rois.append(roi)
        return cls(
            items=rois,
            indices=np.array(dict_["indices"], dtype=np.int32),
            axis_names=dict_["axis_names"],
        )

    def model_validate_json(self, text: str) -> RoiListModel:
        """Validate the json string and return an instance."""
        js = json.loads(text)
        return self.construct(js)
