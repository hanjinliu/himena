from __future__ import annotations

import logging
import numpy as np

from himena import MainWindow
from himena.consts import MonospaceFontFamily, StandardType
from himena.standards.model_meta import ImageMeta

from qtpy import QtWidgets as QtW, QtCore, QtGui

_LOGGER = logging.getLogger(__name__)


class QImageDrawToolWidget(QtW.QWidget):
    def __init__(self, ui: MainWindow):
        self._ui = ui
        super().__init__()
        layout = QtW.QVBoxLayout(self)
        layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
        self._fill_btn = QtW.QPushButton("Fill")
        self._fill_value = QtW.QLineEdit()
        self._fill_value.setFont(QtGui.QFont(MonospaceFontFamily))
        layout.addWidget(self._fill_btn)
        layout.addWidget(self._fill_value)

        self._fill_btn.clicked.connect(self._fill)

    def _fill(self):
        win = self._ui.current_window
        if win is None:
            _LOGGER.info("No window is selected.")
            return
        if not win.is_editable:
            _LOGGER.info("Window is not editable.")
            return
        model = win.to_model()
        if model.type != StandardType.IMAGE:
            _LOGGER.info("Model is not an image.")
            return
        if not isinstance(meta := model.metadata, ImageMeta):
            _LOGGER.info("metadata is not ImageMeta")
            return
        if meta.is_rgb:
            raise NotImplementedError("RGB image is not supported yet.")
        roi = meta.current_roi
        if roi is None:
            _LOGGER.info("No ROI is selected.")
            return
        if not isinstance(arr := model.value, np.ndarray):
            raise ValueError("Model value is not a numpy array.")
        mask = roi.to_mask(arr.shape)
        dtype = np.dtype(arr.dtype)
        arr[mask] = dtype.type(self._fill_value.text())
        win.update_value(arr)
