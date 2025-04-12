from __future__ import annotations

from logging import getLogger
from typing import TYPE_CHECKING, Iterable, Literal
import uuid
import weakref
from qtpy import QtWidgets as QtW, QtCore, QtGui
from qtpy.QtCore import Qt
from superqt import QElidingLabel
from himena.types import WidgetDataModel
from himena.utils.misc import is_subtype
from himena.qt._qsub_window import QSubWindow, QSubWindowArea, get_subwindow
from himena.qt._utils import get_main_window
from himena import _drag

if TYPE_CHECKING:
    from himena.widgets import SubWindow

_LOGGER = getLogger(__name__)
_NONE_TOOLTIP = "Drop a subwindow here by Ctrl+dragging the title bar."


class QModelDropBase(QtW.QGroupBox):
    close_requested = QtCore.Signal(object)  # emit self

    def __init__(
        self, layout: Literal["horizontal", "vertical"] = "horizontal", parent=None
    ):
        super().__init__(parent)
        self._thumbnail = _QImageLabel()
        self._target_id: uuid.UUID | None = None
        self._data_model: WidgetDataModel | None = None
        self._main_window_ref = lambda: None
        self._label = QElidingLabel()
        self._label.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        if layout == "horizontal":
            self._label.setFixedHeight(THUMBNAIL_SIZE.height() + 2)
            _layout = QtW.QHBoxLayout(self)
            _layout.setAlignment(
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop
            )
            self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        else:
            self._label.setMinimumWidth(150)
            _layout = QtW.QVBoxLayout(self)
            _layout.setAlignment(
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft
            )
            self._label.setAlignment(
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
            )
        self._label.setToolTip(_NONE_TOOLTIP)
        _layout.setContentsMargins(1, 1, 1, 1)
        _layout.addWidget(self._thumbnail)
        _layout.addWidget(self._label)

        self._close_btn = QtW.QToolButton()
        self._close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._close_btn.setText("✕")
        self._close_btn.setFixedSize(15, 15)
        self._close_btn.clicked.connect(lambda: self.close_requested.emit(self))
        self._close_btn.setParent(self)
        self._close_btn.hide()

    def _update_btn_pos(self):
        pos_loc = self.rect().topRight() - QtCore.QPoint(
            self._close_btn.width() + 5, -5
        )
        self._close_btn.move(pos_loc)

    def enterEvent(self, a0):
        self._close_btn.show()
        self._update_btn_pos()
        return super().enterEvent(a0)

    def leaveEvent(self, a0):
        rect = self.rect().adjusted(1, 1, -1, -1)
        if not rect.contains(self.mapFromGlobal(QtGui.QCursor.pos())):
            self._close_btn.hide()
        return super().leaveEvent(a0)

    def moveEvent(self, a0):
        self._update_btn_pos()
        return super().moveEvent(a0)

    def resizeEvent(self, a0):
        self._update_btn_pos()
        return super().resizeEvent(a0)

    def subwindow(self) -> SubWindow | None:
        """The dropped subwindow."""
        if self._target_id is None:
            return None
        ui = self._main_window_ref()
        if ui is None:
            return None
        return ui.window_for_id(self._target_id)

    def to_model(self):
        if self._data_model is not None:
            return self._data_model
        if widget := self.subwindow():
            return widget.to_model()
        return None

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
        self.close_requested.connect(lambda: self.set_model(None))

    def sizeHint(self) -> QtCore.QSize:
        return QtCore.QSize(150, 50)

    def enterEvent(self, a0):
        if self._data_model is None and self._target_id is None:
            return None
        return super().enterEvent(a0)

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
        elif model := _drag.get_dragging_model():
            self.set_model(model.data_model())

    def set_model(self, value: WidgetDataModel | None):
        if value is None:
            self._label.setText("Drop here")
            self._label.setToolTip(_NONE_TOOLTIP)
            self._thumbnail.unset_pixmap()
        else:
            self._data_model = value
            self._label.setText(f"✓ {value.value!r}")
            self._label.setToolTip(repr(value))

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
        self.setResizeMode(QtW.QListView.ResizeMode.Adjust)
        self.setAcceptDrops(True)
        self._allowed_types = types  # the model type
        self._layout = layout

    def sizeHint(self) -> QtCore.QSize:
        return QtCore.QSize(250, 200)

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

    def leaveEvent(self, a0):
        for i in range(self.count()):
            item = self.item(i)
            widget = self.itemWidget(item)
            widget.leaveEvent(a0)
        return super().leaveEvent(a0)

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
        item.setFlags(Qt.ItemFlag.ItemIsEnabled)
        if self.flow() == QtW.QListView.Flow.LeftToRight:
            item_widget = QModelListItem(layout="vertical")
            item.setSizeHint(QtCore.QSize(100, 200))
        else:
            item_widget = QModelListItem(layout="horizontal")
            item.setSizeHint(QtCore.QSize(100, THUMBNAIL_SIZE.height() + 2))
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
        """List of models."""
        return [self.itemWidget(self.item(i)).to_model() for i in range(self.count())]

    def set_models(self, value):
        if value is None:
            self.clear()
        else:
            raise ValueError("Cannot set list of WidgetDataModel directly.")

    def windows(self) -> list[SubWindow]:
        """List of subwindows."""
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
    pass


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
