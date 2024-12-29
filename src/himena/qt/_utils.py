from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Callable
import warnings

import numpy as np
from app_model.backends.qt import QModelMenu
import qtpy
from qtpy import QtWidgets as QtW, QtCore
from qtpy import QtGui
from himena import _drag
from himena.types import DragDataModel, WidgetDataModel

if TYPE_CHECKING:
    from numpy.typing import NDArray
    from himena.qt import MainWindowQt


class ArrayQImage:
    """Interface between QImage and numpy array"""

    def __init__(self, qimage: QtGui.QImage):
        self.qimage = qimage

    def __repr__(self) -> str:
        array_repr = repr(self.to_numpy())[5:]  # remove "array"
        return f"{self.__class__.__name__}{array_repr}"

    def __array__(self, dtype=None) -> NDArray[np.uint8]:
        return self.to_numpy()

    def __getitem__(self, key) -> NDArray[np.uint8]:
        return self.to_numpy()[key]

    def to_numpy(self) -> NDArray[np.uint8]:
        return qimage_to_ndarray(self.qimage)

    @property
    def shape(self) -> tuple[int, ...]:
        h, w, c = self.qimage.height(), self.qimage.width(), 4
        return h, w, c

    @property
    def dtype(self) -> np.dtype:
        return np.dtype(np.uint8)


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


def ndarray_to_qimage(arr: NDArray[np.uint8], alpha: int = 255) -> QtGui.QImage:
    arr = np.ascontiguousarray(arr)
    if arr.ndim == 2:
        arr = np.stack([arr] * 3 + [np.full(arr.shape, alpha, dtype=np.uint8)], axis=2)
    else:
        if arr.shape[2] == 3:
            arr = np.ascontiguousarray(
                np.concatenate(
                    [arr, np.full(arr.shape[:2] + (1,), alpha, dtype=np.uint8)],
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
    menu = QModelMenu(menu_id=menu_id, app=app)
    menu.setParent(parent, menu.windowFlags())
    return menu


def drag_model(
    model: WidgetDataModel | DragDataModel,
    *,
    desc: str | None = None,
    source: QtW.QWidget | None = None,
    text_data: str | Callable[[], str] | None = None,
):
    """Create a QDrag object for the given model"""
    drag = QtGui.QDrag(source)
    _drag.drag(model)
    mime = QtCore.QMimeData()
    if text_data is None:
        text_data = repr(model)
    elif callable(text_data):
        text_data = text_data()
    if not isinstance(text_data, str):
        warnings.warn(
            f"`text_data` must be a string, got {text_data!r}. Ignored the input.",
            UserWarning,
            stacklevel=2,
        )
        text_data = ""
    mime.setText(text_data)
    if desc is None:
        desc = "model"
    qlabel = QtW.QLabel(desc)
    pixmap = QtGui.QPixmap(qlabel.size())
    qlabel.render(pixmap)
    drag.setPixmap(pixmap)
    drag.setMimeData(mime)
    drag.destroyed.connect(_drag.clear)
    drag.exec()
