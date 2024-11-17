from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING

from app_model.backends.qt import QModelMenu
import qtpy
from qtpy import QtWidgets as QtW
from qtpy import QtGui, QtCore
from himena.types import ClipboardDataModel
from himena.consts import StandardType
from himena._utils import lru_cache


if TYPE_CHECKING:
    import numpy as np
    from numpy.typing import NDArray
    from himena.qt import MainWindowQt


class ArrayQImage:
    def __init__(self, qimage: QtGui.QImage):
        self.qimage = qimage

    def __array__(self, dtype=None) -> NDArray[np.uint8]:
        return qimage_to_ndarray(self.qimage)


def get_stylesheet_path() -> Path:
    """Get the path to the stylesheet file"""
    return Path(__file__).parent / "style.qss"


def get_clipboard_data() -> ClipboardDataModel | None:
    clipboard = QtW.QApplication.clipboard()
    if clipboard is None:
        return None
    md = clipboard.mimeData()
    if md is None:
        return None
    if md.hasHtml():
        return ClipboardDataModel(value=md.html(), type=StandardType.HTML)
    elif md.hasImage():
        arr = ArrayQImage(clipboard.image())
        return ClipboardDataModel(value=arr, type=StandardType.IMAGE)
    elif md.hasText():
        return ClipboardDataModel(value=md.text(), type=StandardType.TEXT)
    return None


def set_clipboard_data(data: ClipboardDataModel) -> None:
    clipboard = QtW.QApplication.clipboard()
    if clipboard is None:
        return
    if data.is_subtype_of(StandardType.TEXT):
        if data.is_subtype_of(StandardType.HTML):
            md = QtCore.QMimeData()
            md.setHtml(str(data.value))
        clipboard.setText(str(data.value))
    elif data.type == StandardType.IMAGE:
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


def build_qmodel_menu(menu_id: str, app: str, parent: QtW.QWidget) -> QModelMenu:
    menu = _build_qmodel_menu(menu_id, app)
    menu.setParent(parent, menu.windowFlags())
    return menu


@lru_cache(maxsize=8)
def _build_qmodel_menu(menu_id: str, app: str) -> QModelMenu:
    return QModelMenu(menu_id=menu_id, app=app)
