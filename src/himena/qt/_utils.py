from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
from app_model.backends.qt import QModelMenu
import qtpy
from qtpy import QtWidgets as QtW
from qtpy import QtGui
from himena._utils import lru_cache


if TYPE_CHECKING:
    from numpy.typing import NDArray
    from himena.qt import MainWindowQt


class ArrayQImage:
    """Interface between QImage and numpy array"""

    def __init__(self, qimage: QtGui.QImage):
        self.qimage = qimage

    def __array__(self, dtype=None) -> NDArray[np.uint8]:
        return qimage_to_ndarray(self.qimage)

    def __getitem__(self, key) -> NDArray[np.uint8]:
        return self.__array__()[key]

    @property
    def shape(self) -> tuple[int, ...]:
        return self.__array__().shape

    @property
    def dtype(self) -> np.dtype:
        return np.uint8


def get_stylesheet_path() -> Path:
    """Get the path to the stylesheet file"""
    return Path(__file__).parent / "style.qss"


def qimage_to_ndarray(img: QtGui.QImage) -> NDArray[np.uint8]:
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


def ndarray_to_qimage(arr: NDArray[np.uint8]) -> QtGui.QImage:
    if arr.ndim == 2:
        arr = np.stack([arr] * 3 + [np.full(arr.shape, 255, dtype=np.uint8)], axis=2)
    else:
        if arr.shape[2] == 3:
            arr = np.ascontiguousarray(
                np.concatenate(
                    [arr, np.full(arr.shape[:2] + (1,), 255, dtype=np.uint8)],
                    axis=2,
                )
            )
        elif arr.shape[2] != 4:
            raise ValueError(
                "The shape of an RGB image must be (M, N), (M, N, 3) or (M, N, 4), "
                f"got {arr.shape!r}."
            )
    return QtGui.QImage(
        arr, arr.shape[1], arr.shape[0], QtGui.QImage.Format.Format_RGBA8888
    )


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
