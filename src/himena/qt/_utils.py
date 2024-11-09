from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING
import qtpy
from qtpy import QtWidgets as QtW
from qtpy import QtGui, QtCore
from himena.types import ClipboardDataModel
from himena.consts import StandardTypes, StandardSubtypes

if TYPE_CHECKING:
    import numpy as np
    from numpy.typing import NDArray
    from himena.qt import MainWindowQt


class ArrayQImage:
    def __init__(self, qimage: QtGui.QImage):
        self.qimage = qimage

    def __array__(self, dtype=None) -> NDArray[np.uint8]:
        return qimage_to_ndarray(self.qimage)


def get_clipboard_data() -> ClipboardDataModel | None:
    clipboard = QtW.QApplication.clipboard()
    if clipboard is None:
        return None
    md = clipboard.mimeData()
    if md is None:
        return None
    if md.hasHtml():
        return ClipboardDataModel(value=md.html(), type=StandardSubtypes.HTML)
    elif md.hasImage():
        arr = ArrayQImage(clipboard.image())
        return ClipboardDataModel(value=arr, type=StandardTypes.IMAGE)
    elif md.hasText():
        return ClipboardDataModel(value=md.text(), type=StandardTypes.TEXT)
    return None


def set_clipboard_data(data: ClipboardDataModel) -> None:
    clipboard = QtW.QApplication.clipboard()
    if clipboard is None:
        return
    if data.is_subtype_of(StandardTypes.TEXT):
        if data.is_subtype_of(StandardSubtypes.HTML):
            md = QtCore.QMimeData()
            md.setHtml(str(data.value))
        clipboard.setText(str(data.value))
    elif data.type == StandardTypes.IMAGE:
        if isinstance(data.value, ArrayQImage):
            img = data.value.qimage
        else:
            raise NotImplementedError
        clipboard.setImage(img)


def qimage_to_ndarray(img: QtGui.QImage) -> NDArray[np.uint8]:
    import numpy as np

    if img.format() != QtGui.QImage.Format.Format_ARGB32:
        img = img.convertToFormat(QtGui.QImage.Format.Format_ARGB32)
    b = img.constBits()
    h, w, c = img.height(), img.width(), 4

    if qtpy.API_NAME.startswith("PySide"):
        arr = np.array(b).reshape(h, w, c)
    else:
        b.setsize(h * w * c)
        arr = np.frombuffer(b, np.uint8).reshape(h, w, c)

    arr = arr[:, :, [2, 1, 0, 3]]
    return arr


@contextmanager
def qsignal_blocker(widget: QtW.QWidget):
    was_blocked = widget.signalsBlocked()
    widget.blockSignals(True)
    try:
        yield
    finally:
        widget.blockSignals(was_blocked)


def get_main_window(widget: QtW.QWidget) -> MainWindowQt:
    """Traceback the main window from the given widget"""
    parent = widget
    while parent is not None:
        parent = parent.parentWidget()
        if isinstance(parent, QtW.QMainWindow):
            return parent._himena_main_window
    raise ValueError("No mainwindow found.")
