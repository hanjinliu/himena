from __future__ import annotations

import qtpy
from qtpy import QtWidgets as QtW
from qtpy import QtGui
from royalapp.types import ClipBoardDataModel
from royalapp.consts import StandardTypes


def get_clipboard_data() -> ClipBoardDataModel | None:
    clipboard = QtW.QApplication.clipboard()
    if clipboard is None:
        return None
    md = clipboard.mimeData()
    if md is None:
        return None
    if md.hasHtml():
        return ClipBoardDataModel(value=md.html(), type=StandardTypes.HTML)
    elif md.hasImage():
        arr = qimage_to_ndarray(clipboard.image())
        return ClipBoardDataModel(value=arr, type=StandardTypes.IMAGE)
    elif md.hasText():
        return ClipBoardDataModel(value=md.text(), type=StandardTypes.TEXT)
    return None


def qimage_to_ndarray(img: QtGui.QImage):
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
