from __future__ import annotations

from qtpy import QtWidgets as QtW, QtCore
import numpy as np


_SUPPORTED_DTYPE_DEPTH = {
    "int": [8, 16, 32, 64],
    "uint": [8, 16, 32, 64],
    "float": [16, 32, 64, 128],
    "complex": [64, 128, 256],
    "bool": [],
}


class QNumericDTypeEdit(QtW.QWidget):
    valueChanged = QtCore.Signal(object)

    def __init__(self, parent=None):
        super().__init__()
        layout = QtW.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(1)
        self._combo_type = QtW.QComboBox()
        self._combo_type.addItems(["int", "uint", "float", "complex", "bool"])
        self._combo_type.setCurrentIndex(0)
        self._combo_depth = QtW.QComboBox()
        _fixed = QtW.QSizePolicy.Policy.Fixed
        self._combo_depth.setSizePolicy(_fixed, _fixed)

        layout.addWidget(self._combo_type)
        layout.addWidget(self._combo_depth)

        self._combo_type.currentTextChanged.connect(self._type_changed)
        self._type_changed(self._combo_type.currentText())  # initialize

        # self.setFixedHeight(28)

    def _type_changed(self, text: str):
        self._combo_depth.clear()
        self._combo_depth.addItems([str(d) for d in _SUPPORTED_DTYPE_DEPTH[text]])
        self._combo_depth.setCurrentIndex(0)

    def _cast_dtype(self, dtype) -> np.dtype:
        return np.dtype(dtype)

    def dtype(self) -> np.dtype:
        return self._cast_dtype(
            f"{self._combo_type.currentText()}{self._combo_depth.currentText()}"
        )

    def set_dtype(self, dtype: np.dtype):
        dtype = self._cast_dtype(dtype)
        self._combo_type.setCurrentText(dtype.kind)
        self._combo_depth.setCurrentText(str(dtype.itemsize * 8))
