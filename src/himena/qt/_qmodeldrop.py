from __future__ import annotations

from logging import getLogger
from typing import TYPE_CHECKING, Iterable, Literal
import uuid
import weakref
from qtpy import QtWidgets as QtW, QtCore, QtGui
from qtpy.QtCore import Qt
from himena.types import WidgetDataModel
from himena.utils.misc import is_subtype
from himena.qt._qsub_window import QSubWindow, QSubWindowArea, get_subwindow
from himena.qt._utils import get_main_window
from himena import _drag

if TYPE_CHECKING:
    from himena.widgets import SubWindow

_LOGGER = getLogger(__name__)


class QModelDropBase(QtW.QGroupBox):
    def __init__(
        self, layout: Literal["horizontal", "vertical"] = "horizontal", parent=None
    ):
        super().__init__(parent)
        self._thumbnail = _QImageLabel()
        self._target_id: int | None = None
        self._main_window_ref = lambda: None
        self._label = QtW.QLabel()
        self._label.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        if layout == "horizontal":
            self._label.setFixedHeight(THUMBNAIL_SIZE.height() + 2)
            _layout = QtW.QHBoxLayout(self)
        else:
            self._label.setFixedWidth(THUMBNAIL_SIZE.width() + 6)
            _layout = QtW.QVBoxLayout(self)
        self._label.setToolTip("Drop a subwindow here by Ctrl+dragging the title bar.")
        _layout.setContentsMargins(1, 1, 1, 1)
        _layout.addWidget(self._thumbnail)
        _layout.addWidget(self._label)

    def subwindow(self) -> SubWindow | None:
        """The dropped subwindow."""
        if self._target_id is None:
            return None
        ui = self._main_window_ref()
        if ui is None:
            return None
        return ui.window_for_id(self._target_id)

    def set_qsubwindow(self, src: QSubWindow):
        src_wrapper = src._my_wrapper()
        self._thumbnail.set_pixmap(
            src._pixmap_resized(THUMBNAIL_SIZE, QtGui.QColor("#f0f0f0"))
        )
        self._target_id = src_wrapper._identifier
        self._main_window_ref = weakref.ref(get_main_window(src))
        self._label.setText(src.windowTitle())

    def set_subwindow(self, src: SubWindow):
        self.set_qsubwindow(get_subwindow(src.widget))

    def to_model(self) -> WidgetDataModel | None:
        if widget := self.subwindow():
            return widget.to_model()
        return None

    def set_model(self, value: WidgetDataModel | None):
        if value is None:
            self._label.setText("Drop here")
            self._thumbnail.unset_pixmap()
        else:
            raise ValueError("Cannot set WidgetDataModel directly.")


class QModelDrop(QModelDropBase):
    """Widget for dropping model data from a subwindow."""

    valueChanged = QtCore.Signal(WidgetDataModel)
    windowChanged = QtCore.Signal(object)

    def __init__(
        self,
        types: list[str] | None = None,
        layout: Literal["horizontal", "vertical"] = "horizontal",
        parent: QtW.QWidget | None = None,
    ):
        super().__init__(layout, parent)
        self.setAcceptDrops(True)
        self._label.setText("Drop here")
        self._label.setAlignment(
            Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
        )
        self._allowed_types = types  # the model type
        self._target_id: uuid.UUID | None = None
        self._data_model: WidgetDataModel | None = None

    def sizeHint(self) -> QtCore.QSize:
        return QtCore.QSize(150, 50)

    def dragEnterEvent(self, event: QtGui.QDragEnterEvent):
        if isinstance(src := event.source(), QSubWindow):
            widget = src._widget
            if not hasattr(widget, "to_model"):
                _LOGGER.debug("Ignoring drop event")
                event.ignore()
                event.setDropAction(Qt.DropAction.IgnoreAction)
                return
            model_type = getattr(widget, "model_type", lambda: None)()
            _LOGGER.info("Entered model type %s", model_type)
            if self._is_type_maches(model_type):
                _LOGGER.debug("Accepting drop event")
                event.accept()
                return
        elif isinstance(area := event.source(), QSubWindowArea):
            subwindows = area.subWindowList()
            if len(subwindows) == 1:
                event.accept()
                return
        elif model := _drag.get_dragging_model():
            if self._is_type_maches(model.type):
                _LOGGER.debug("Accepting drop event")
                event.accept()
                return
        event.ignore()
        event.setDropAction(Qt.DropAction.IgnoreAction)

    def dropEvent(self, event: QtGui.QDropEvent):
        if isinstance(win := event.source(), QSubWindow):
            self._drop_qsubwindow(win)
        elif isinstance(area := event.source(), QSubWindowArea):
            subwindows = area.subWindowList()
            if len(subwindows) == 1:
                self._drop_qsubwindow(subwindows[0])

    def _drop_qsubwindow(self, win: QSubWindow):
        widget = win._widget
        model_type = getattr(widget, "model_type", lambda: None)()
        _LOGGER.info("Dropped model type %s", model_type)
        if self._is_type_maches(model_type):
            _LOGGER.info("Dropped model %s", win.windowTitle())
            self.set_qsubwindow(win)
            self._emit_window(win._my_wrapper())

    def _emit_window(self, win: SubWindow):
        self.windowChanged.emit(win)
        if win.supports_to_model:
            self.valueChanged.emit(win.to_model())

    def _on_source_closed(self):
        self._target_id = None

    def _is_type_maches(self, model_type: str) -> bool:
        if self._allowed_types is None:
            return True
        return any(is_subtype(model_type, t) for t in self._allowed_types)


class QModelDropList(QtW.QListWidget):
    modelsChanged = QtCore.Signal(list)
    windowsChanged = QtCore.Signal(list)

    def __init__(
        self,
        types: list[str] | None = None,
        layout: Literal["horizontal", "vertical"] = "vertical",
        parent: QtW.QWidget | None = None,
    ):
        super().__init__(parent)
        if layout == "horizontal":
            self.setFlow(QtW.QListView.Flow.LeftToRight)
        else:
            self.setFlow(QtW.QListView.Flow.TopToBottom)
        self.setAcceptDrops(True)
        self._allowed_types = types  # the model type
        self._layout = layout

    def sizeHint(self) -> QtCore.QSize:
        return QtCore.QSize(150, 100)

    def dragEnterEvent(self, event: QtGui.QDragEnterEvent):
        if isinstance(src := event.source(), QSubWindow):
            widget = src._widget
            if not hasattr(widget, "to_model"):
                _LOGGER.debug("Ignoring drop event")
                event.ignore()
                event.setDropAction(Qt.DropAction.IgnoreAction)
                return
            model_type = getattr(widget, "model_type", lambda: None)()
            _LOGGER.info("Entered model type: %s", model_type)
            if self._is_type_maches(model_type):
                _LOGGER.debug("Accepting drop event")
                event.accept()
                event.setDropAction(Qt.DropAction.MoveAction)
                return
        elif isinstance(area := event.source(), QSubWindowArea):
            subwindows = area.subWindowList()
            if len(subwindows) == 1:
                event.accept()
                return
        elif model := _drag.get_dragging_model():
            if self._is_type_maches(model.type):
                _LOGGER.debug("Accepting drop event")
                event.accept()
                event.setDropAction(Qt.DropAction.MoveAction)
                return
        event.ignore()
        event.setDropAction(Qt.DropAction.IgnoreAction)

    def dragMoveEvent(self, e: QtGui.QDragMoveEvent):
        e.acceptProposedAction()
        return

    def dropEvent(self, event: QtGui.QDropEvent):
        if isinstance(win := event.source(), QSubWindow):
            self._drop_qsubwindow(win)
            event.accept()
            return
        elif isinstance(area := event.source(), QSubWindowArea):
            subwindows = area.subWindowList()
            if len(subwindows) == 1:
                self._drop_qsubwindow(subwindows[0])
                event.accept()
                return
        event.ignore()
        event.setDropAction(Qt.DropAction.IgnoreAction)
        return None

    def _is_type_maches(self, model_type: str) -> bool:
        if self._allowed_types is None:
            return True
        return any(is_subtype(model_type, t) for t in self._allowed_types)

    def _drop_qsubwindow(self, win: QSubWindow):
        widget = win._widget
        model_type = getattr(widget, "model_type", lambda: None)()
        _LOGGER.info("Dropped model type %s", model_type)
        if self._is_type_maches(model_type):
            _LOGGER.info("Dropped model %s", win.windowTitle())
            self._append_sub_window(win)
            self.windowsChanged.emit(self.windows())
            self.modelsChanged.emit(self.models())

    def _append_item(self) -> QModelListItem:
        item = QtW.QListWidgetItem()
        self.addItem(item)
        item.setSizeHint(QtCore.QSize(100, THUMBNAIL_SIZE.height() + 2))
        if self.flow() == QtW.QListView.Flow.LeftToRight:
            item_widget = QModelListItem(layout="vertical")
        else:
            item_widget = QModelListItem(layout="horizontal")
        self.setItemWidget(item, item_widget)
        item_widget.close_requested.connect(self._remove_item)
        return item_widget

    def _append_sub_window(self, src: QSubWindow):
        item_widget = self._append_item()
        item_widget.set_qsubwindow(src)
        win = src._my_wrapper()
        win.closed.connect(lambda: self._remove_item(item_widget))

    def _remove_item(self, item: QModelListItem):
        for i in range(self.count()):
            if self.itemWidget(self.item(i)) is item:
                self.takeItem(i)
                return
        raise ValueError(f"Item {item} not found")

    def models(self) -> list[WidgetDataModel]:
        return [self.itemWidget(self.item(i)).to_model() for i in range(self.count())]

    def set_models(self, value):
        if value is None:
            self.clear()
        else:
            raise ValueError("Cannot set list of WidgetDataModel directly.")

    def windows(self) -> list[SubWindow]:
        return [self.itemWidget(self.item(i)).subwindow() for i in range(self.count())]

    def set_windows(self, value: Iterable[SubWindow] | None):
        self.clear()
        if value is not None:
            for win in value:
                qwin = get_subwindow(win.widget)
                self._append_sub_window(qwin)

    if TYPE_CHECKING:

        def itemWidget(self, item: QtW.QListWidgetItem) -> QModelListItem: ...


class QModelListItem(QModelDropBase):
    close_requested = QtCore.Signal(object)  # emit self

    def __init__(self, layout: Literal["horizontal", "vertical"] = "horizontal"):
        super().__init__(layout)
        self._close_btn = QtW.QToolButton()
        self._close_btn.setText("✕")
        self._close_btn.setFixedSize(15, 15)
        self._close_btn.clicked.connect(lambda: self.close_requested.emit(self))
        self._close_btn.setParent(
            self, self._close_btn.windowFlags() | Qt.WindowType.FramelessWindowHint
        )
        self._close_btn.hide()

    def enterEvent(self, a0):
        self._close_btn.show()
        pos_loc = self.rect().topRight() - QtCore.QPoint(
            self._close_btn.width() + 5, -5
        )
        self._close_btn.move(self.mapToGlobal(pos_loc))
        return super().enterEvent(a0)

    def leaveEvent(self, a0):
        self._close_btn.hide()
        return super().leaveEvent(a0)


THUMBNAIL_SIZE = QtCore.QSize(36, 36)


class _QImageLabel(QtW.QLabel):
    def __init__(self):
        super().__init__()
        self.setAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignTop)
        self.setSizePolicy(
            QtW.QSizePolicy.Policy.Expanding, QtW.QSizePolicy.Policy.Expanding
        )
        self.setFixedSize(0, 0)

    def set_pixmap(self, pixmap: QtGui.QPixmap):
        self.setFixedSize(THUMBNAIL_SIZE)
        sz = self.size()
        self.setPixmap(
            pixmap.scaled(
                sz,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

    def unset_pixmap(self):
        self.setFixedSize(0, 0)
        self.clear()
