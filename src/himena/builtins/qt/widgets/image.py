from __future__ import annotations

from typing import TYPE_CHECKING
from qtpy import QtWidgets as QtW
from qtpy import QtGui, QtCore
from superqt import QLabeledSlider
from himena.consts import StandardTypes
from himena.types import WidgetDataModel
from himena.qt._magicgui._toggle_switch import QLabeledToggleSwitch

if TYPE_CHECKING:
    import numpy as np
    from numpy.typing import NDArray


class _QImageLabel(QtW.QLabel):
    def __init__(self, val):
        super().__init__()
        self._transformation = QtCore.Qt.TransformationMode.SmoothTransformation
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
        else:
            if val.shape[2] == 3:
                val = np.ascontiguousarray(
                    np.concatenate(
                        [val, np.full(val.shape[:2] + (1,), 255, dtype=np.uint8)],
                        axis=2,
                    )
                )
            elif val.shape[2] != 4:
                raise ValueError(
                    "The shape of an RGB image must be (M, N), (M, N, 3) or (M, N, 4), "
                    f"got {val.shape!r}."
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
                self._transformation,
            )
        )

    def resizeEvent(self, ev: QtGui.QResizeEvent) -> None:
        self._update_pixmap()


class QDefaultImageView(QtW.QWidget):
    def __init__(self):
        import numpy as np

        super().__init__()
        layout = QtW.QVBoxLayout(self)
        self._sliders: list[QtW.QSlider] = []

        self._image_label = _QImageLabel(np.zeros((1, 1), dtype=np.uint8))
        layout.addWidget(self._image_label)

        self._control = QImageViewControl()
        self._control.interpolation_changed.connect(self._interpolation_changed)
        self._arr: NDArray[np.int8] | None = None

    def update_model(self, model: WidgetDataModel[NDArray[np.uint8]]):
        import numpy as np

        arr = np.asarray(model.value)
        ndim = arr.ndim - 2
        if arr.shape[-1] in (3, 4) and ndim > 0:
            ndim -= 1

        sl_0 = (0,) * ndim
        self._image_label.set_array(self.as_image_array(arr[sl_0]))

        nsliders = len(self._sliders)
        if nsliders > ndim:
            for i in range(ndim, nsliders):
                self._sliders[i].setVisible(False)
        elif nsliders < ndim:
            for i in range(nsliders, ndim):
                self._make_slider(model.value.shape[i])
        self._slider_changed()
        self._arr = arr

    def to_model(self) -> WidgetDataModel[NDArray[np.uint8]]:
        assert self._arr is not None
        return WidgetDataModel(
            value=self._arr,
            type=self.model_type(),
            extension_default=".png",
        )

    def model_type(self) -> str:
        return StandardTypes.IMAGE

    def size_hint(self) -> tuple[int, int]:
        return 400, 400

    def is_editable(self) -> bool:
        return False

    def control_widget(self) -> QtW.QWidget:
        return self._control

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

    def _slider_changed(self):
        if self._arr is None:
            return
        sl = tuple(sl.value() for sl in self._sliders)
        arr = self.as_image_array(self._arr[sl])
        self._image_label.set_array(arr)

    def _interpolation_changed(self, checked: bool):
        if checked:
            tr = QtCore.Qt.TransformationMode.SmoothTransformation
        else:
            tr = QtCore.Qt.TransformationMode.FastTransformation
        self._image_label._transformation = tr
        self._image_label._update_pixmap()

    def _make_slider(self, size: int):
        slider = QLabeledSlider(QtCore.Qt.Orientation.Horizontal)
        self._sliders.append(slider)
        self.layout().addWidget(slider, alignment=QtCore.Qt.AlignmentFlag.AlignBottom)
        slider.setRange(0, size - 1)
        slider.valueChanged.connect(self._slider_changed)
        return slider


class QImageViewControl(QtW.QWidget):
    interpolation_changed = QtCore.Signal(bool)

    def __init__(self):
        super().__init__()
        layout = QtW.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)

        self._interpolation_check_box = QLabeledToggleSwitch()
        self._interpolation_check_box.setText("smooth")
        self._interpolation_check_box.setChecked(True)
        self._interpolation_check_box.setMaximumHeight(36)
        self._interpolation_check_box.toggled.connect(self.interpolation_changed.emit)
        layout.addWidget(self._interpolation_check_box)
