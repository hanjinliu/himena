from __future__ import annotations

from qtpy import QtWidgets as QtW, QtCore, QtGui
import numpy as np
from numpy.typing import NDArray

from himena.qt import ndarray_to_qimage


class QViewBox(QtW.QWidget):
    def __init__(self, parent: QtW.QWidget | None = None):
        super().__init__(parent)
        self._next_qpixmap: QtGui.QPixmap | None = None
        self._arr = None  # to avoid garbage collection
        if self.__class__.make_pixmap is QViewBox.make_pixmap:
            raise NotImplementedError(
                "Subclasses of QViewBox must implement make_pixmap method."
            )

    def paintEvent(self, _event: QtGui.QPaintEvent) -> None:
        painter = QtGui.QPainter(self)
        if self._next_qpixmap is not None:
            painter.drawPixmap(0, 0, self._next_qpixmap)
        painter.end()

    def resizeEvent(self, a0):
        super().resizeEvent(a0)
        self._store_qpixmap(self.size())

    def _store_qpixmap(self, size: QtCore.QSize):
        ratio = self.devicePixelRatioF()
        scaled_size = QtCore.QSize(
            int(size.width() * ratio), int(size.height() * ratio)
        )
        self._arr = self.make_pixmap(scaled_size)
        qimg = ndarray_to_qimage(self._arr)
        self._next_qpixmap = QtGui.QPixmap.fromImage(qimg)
        self._next_qpixmap.setDevicePixelRatio(ratio)

    def make_pixmap(self, size: QtCore.QSize) -> NDArray[np.uint8]:
        """Override this method to provide the image array for the given size."""
