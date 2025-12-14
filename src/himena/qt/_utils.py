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
        array_repr = f"<shape={self.shape}, dtype={self.dtype}>"
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

    @classmethod
    def from_qwidget(cls, widget: QtW.QWidget) -> ArrayQImage:
        return cls(widget.grab().toImage())


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
    """Build a QModelMenu of the given ID."""
    menu = QModelMenu(menu_id=menu_id, app=app)
    menu.setParent(parent, menu.windowFlags())
    menu.setToolTipsVisible(True)
    return menu


def drag_files(
    path_or_paths: str | Path | list[str | Path],
    /,
    *,
    desc: str | None = None,
    source: QtW.QWidget | None = None,
    exec: bool = True,
    plugin: str | None = None,
) -> QtGui.QDrag:
    """Create a QDrag object for the given file path(s).

    Mouse drag object constructed by this function is equivalent to dragging files from
    the file explorer etc.

    Parameters
    ----------
    path_or_paths : str | Path | list[str | Path]
        The file path or list of file paths to drag.
    desc : str, optional
        The description of the drag. This will be shown in the drag image.
    source : QWidget, optional
        The widget that is the source of the drag.
    exec : bool, default True
        Whether to execute the drag immediately. Setting this to false is useful when
        you want to test the QDrag object construction.
    """
    drag = QtGui.QDrag(source)
    mime = QtCore.QMimeData()
    if isinstance(path_or_paths, (str, Path)):
        paths = [Path(path_or_paths)]
    else:
        paths = [Path(p) for p in path_or_paths]
    url_list = [QtCore.QUrl.fromLocalFile(str(p.resolve())) for p in paths]
    mime.setUrls(url_list)
    if desc is None:
        _s = "s" if len(paths) > 1 else ""
        desc = f"{len(paths)} file{_s}"
    if plugin is not None:
        mime.setData("text/himena-open-plugin", plugin.encode())
    drag.setPixmap(_text_to_pixmap(desc, source))
    drag.setMimeData(mime)
    if exec:
        drag.exec()
    return drag


def drag_model(
    model: WidgetDataModel | DragDataModel,
    *,
    desc: str | None = None,
    source: QtW.QWidget | None = None,
    text_data: str | Callable[[], str] | None = None,
    exec: bool = True,
) -> QtGui.QDrag:
    """Create a QDrag object for the given model."""
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
    drag.setPixmap(_text_to_pixmap(desc, source))
    drag.setMimeData(mime)
    drag.destroyed.connect(_drag.clear)
    cursor = QtGui.QCursor(QtCore.Qt.CursorShape.OpenHandCursor)
    drag.setDragCursor(cursor.pixmap(), QtCore.Qt.DropAction.MoveAction)
    if exec:
        drag.exec()
    return drag


def drag_command(
    source: QtW.QWidget,
    command_id: str,
    type: str | None = None,
    *,
    with_params: dict[str, object] | None = None,
    desc: str | None = None,
    text_data: str | Callable[[], str] | None = None,
    exec: bool = True,
) -> QtGui.QDrag:
    """Drag a command that will be executed when dropped.

    Parameters
    ----------
    source : QWidget
        The widget that is the source of the drag. This is also used to find the input
        subwindow and the main window.
    command_id : str
        The command ID to execute when the drag is dropped.
    type : str
        The output type of the command.
    with_params : dict[str, object], optional
        Additional parameters to pass to the command. This parameter will be forwarded
        to `ui.exec_action`.
    desc : str, optional
        The description of the drag. This will be shown in the drag image.
    text_data : str or callable, optional
        The text data to set in the drag. If a callable is provided, it will be called
        to get the text data. This text data will be set as a fallback data in the drag,
        e.g. dropped to an external text editor.
    exec : bool, default True
        Whether to execute the drag immediately.
    """

    def _cb():
        ui = get_main_window(source)
        win = None
        for win in ui.iter_windows():
            front = win._split_interface_and_frontend()[1]
            if front is source:
                break
        if win is None:
            raise ValueError("No subwindow found for the dragging widget.")
        if win.supports_to_model:
            model = win.to_model()
        else:
            model = None
        out = ui.exec_action(
            command_id,
            window_context=win,
            model_context=model,
            with_params=with_params,
            process_model_output=False,
        )
        return out

    return drag_model(
        DragDataModel(getter=_cb, type=type),
        desc=desc,
        text_data=text_data,
        source=source,
        exec=exec,
    )


def _text_to_pixmap(text: str, parent=None) -> QtGui.QPixmap:
    qlabel = QtW.QLabel(text)
    pixmap = QtGui.QPixmap(qlabel.size())
    pixmap.setDevicePixelRatio(qlabel.devicePixelRatioF())
    qlabel.render(pixmap)
    return pixmap
