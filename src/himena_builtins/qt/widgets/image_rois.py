from __future__ import annotations

from typing import TYPE_CHECKING
from qtpy import QtWidgets as QtW
from himena.plugins import protocol_override
from himena.standards import roi
from himena.consts import StandardType
from himena.types import WidgetDataModel
from ._image_components import QSimpleRoiCollection

if TYPE_CHECKING:
    pass


class QImageRoiView(QtW.QWidget):
    """The ROI list widget"""

    __himena_widget_id__ = "builtins:QImageRoiView"
    __himena_display_name__ = "Built-in Image ROI Viewer"

    def __init__(self):
        super().__init__()

        layout = QtW.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._roi_collection = QSimpleRoiCollection()
        layout.addWidget(self._roi_collection)
        self._is_modified = False
        self._model_type = StandardType.IMAGE_ROIS

    @protocol_override
    def update_model(self, model: WidgetDataModel):
        value = model.value
        if callable(value):
            value = value()
        if not isinstance(value, roi.RoiListModel):
            raise ValueError(f"Expected a RoiListModel, got {type(value)}")
        self._roi_collection.clear()
        self._roi_collection.update_from_standard_roi_list(value)
        self._model_type = model.type

    @protocol_override
    def to_model(self) -> WidgetDataModel:
        return WidgetDataModel(
            value=self._roi_collection.to_standard_roi_list(),
            type=self.model_type(),
            extension_default=".roi.json",
        )

    @protocol_override
    def model_type(self) -> str:
        return self._model_type

    @protocol_override
    def is_modified(self) -> bool:
        return self._is_modified

    @protocol_override
    def set_modified(self, modified: bool):
        self._is_modified = modified

    @protocol_override
    def size_hint(self) -> tuple[int, int]:
        return 180, 300
