from __future__ import annotations

from typing import TYPE_CHECKING
from qtpy import QtWidgets as QtW
from qtpy import QtGui, QtCore
from superqt import QLabeledSlider
from royalapp.types import WidgetDataModel

if TYPE_CHECKING:
    import numpy as np
    from numpy.typing import NDArray


class _QImageLabel(QtW.QLabel):
    def __init__(self, val):
        super().__init__()
        self.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.setSizePolicy(
            QtW.QSizePolicy.Policy.Expanding, QtW.QSizePolicy.Policy.Expanding
        )
        self.set_array(val)

    def set_array(self, val: NDArray[np.uint8]):
        import numpy as np

        if val.ndim == 2:
            val = np.stack(
                [val] * 3 + [np.full(val.shape, 255, dtype=np.uint8)], axis=2
            )
        image = QtGui.QImage(
            val, val.shape[1], val.shape[0], QtGui.QImage.Format.Format_RGBA8888
        )
        self._pixmap_orig = QtGui.QPixmap.fromImage(image)
        self._update_pixmap()

    def _update_pixmap(self):
        sz = self.size()
        self.setPixmap(
            self._pixmap_orig.scaled(
                sz,
                QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                QtCore.Qt.TransformationMode.SmoothTransformation,
            )
        )

    def resizeEvent(self, ev: QtGui.QResizeEvent) -> None:
        self._update_pixmap()


class QDefaultImageView(QtW.QWidget):
    def __init__(self, model: WidgetDataModel[NDArray[np.uint8]]):
        super().__init__()
        layout = QtW.QVBoxLayout()
        ndim = model.value.ndim - 2
        if model.value.shape[-1] in (3, 4):
            ndim -= 1
        sl_0 = (0,) * ndim
        self._image_label = _QImageLabel(self.as_image_array(model.value[sl_0]))
        layout.addWidget(self._image_label)

        self._sliders: list[QtW.QSlider] = []
        for i in range(ndim):
            slider = QLabeledSlider(QtCore.Qt.Orientation.Horizontal)
            self._sliders.append(slider)
            layout.addWidget(slider, alignment=QtCore.Qt.AlignmentFlag.AlignBottom)
            slider.setRange(0, model.value.shape[i] - 1)
            slider.valueChanged.connect(self._slider_changed)
        self.setLayout(layout)
        self._model = model

    def _slider_changed(self):
        sl = tuple(sl.value() for sl in self._sliders)
        arr = self.as_image_array(self._model.value[sl])
        self._image_label.set_array(arr)

    @classmethod
    def from_model(cls, model: WidgetDataModel) -> QDefaultImageView:
        self = cls(model)
        if model.source is not None:
            self.setObjectName(model.source.name)
        return self

    def to_model(self) -> WidgetDataModel:
        return WidgetDataModel(
            value=self._model.value,
            type=self._model.type,
        )

    def model_type(self) -> str:
        return self._model.type

    def size_hint(self) -> tuple[int, int]:
        return 400, 400

    def as_image_array(self, arr: np.ndarray) -> NDArray[np.uint8]:
        import numpy as np

        if arr.dtype == "uint8":
            arr0 = arr
        elif arr.dtype == "uint16":
            arr0 = (arr / 256).astype("uint8")
        elif arr.dtype.kind == "f":
            min_ = arr.min()
            max_ = arr.max()
            if min_ < max_:
                arr0 = ((arr - min_) / (max_ - min_) * 255).astype("uint8")
            else:
                arr0 = np.zeros(arr.shape, dtype=np.uint8)
        else:
            raise ValueError(f"Unsupported data type: {arr.dtype}")
        return np.ascontiguousarray(arr0)
