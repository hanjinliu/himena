from __future__ import annotations

from typing import TYPE_CHECKING
from qtpy import QtWidgets as QtW
from himena.plugins import validate_protocol
from himena.qt._utils import drag_model
from himena.standards import roi
from himena.standards.model_meta import ImageRoisMeta, ArrayAxis
from himena.consts import StandardType
from himena.types import DragDataModel, WidgetDataModel
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
        self._model_type = StandardType.ROIS
        self._axes: list[ArrayAxis] | None = None
        self._roi_collection.drag_requested.connect(self._run_drag_model)

    @validate_protocol
    def update_model(self, model: WidgetDataModel):
        value = model.value
        if callable(value):
            value = value()
        if not isinstance(value, roi.RoiListModel):
            raise ValueError(f"Expected a RoiListModel, got {type(value)}")
        self._roi_collection.clear()
        self._roi_collection.update_from_standard_roi_list(value)
        self._model_type = model.type
        if isinstance(meta := model.metadata, ImageRoisMeta):
            if meta.axes:
                self._axes = meta.axes
            if meta.selections:
                self._roi_collection.set_selections(meta.selections)

    @validate_protocol
    def to_model(self) -> WidgetDataModel:
        return WidgetDataModel(
            value=self._roi_collection.to_standard_roi_list(),
            type=self.model_type(),
            extension_default=".roi.json",
            metadata=ImageRoisMeta(
                axes=self._axes,
                selections=self._roi_collection.selections(),
            ),
        )

    @validate_protocol
    def model_type(self) -> str:
        return self._model_type

    @validate_protocol
    def is_modified(self) -> bool:
        return self._is_modified

    @validate_protocol
    def set_modified(self, modified: bool):
        self._is_modified = modified

    @validate_protocol
    def size_hint(self) -> tuple[int, int]:
        return 180, 300

    def _run_drag_model(self, indices: list[int]):
        def make_model():
            rlist = self._roi_collection.to_standard_roi_list(indices)
            axes = self._axes
            return WidgetDataModel(
                value=rlist,
                type=StandardType.ROIS,
                title="ROIs",
                metadata=ImageRoisMeta(axes=axes),
            )

        nrois = len(indices)
        _s = "" if nrois == 1 else "s"
        drag_model(
            model=DragDataModel(getter=make_model, type=StandardType.ROIS),
            desc=f"{nrois} ROI{_s}",
            source=self,
        )
