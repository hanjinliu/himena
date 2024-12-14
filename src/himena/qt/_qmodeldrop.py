from __future__ import annotations

from logging import getLogger
from typing import TYPE_CHECKING
from qtpy import QtWidgets as QtW, QtCore, QtGui
from qtpy.QtCore import Qt
from himena.types import WidgetDataModel, is_subtype
from himena.qt._qsub_window import QSubWindow, QSubWindowArea
from himena.qt._utils import get_main_window

if TYPE_CHECKING:
    from himena.widgets import SubWindow

_LOGGER = getLogger(__name__)


class QModelDrop(QtW.QGroupBox):
    """Widget for dropping model data from a subwindow."""

    valueChanged = QtCore.Signal(WidgetDataModel)

    def __init__(
        self,
        types: list[str] | None = None,
        parent: QtW.QWidget | None = None,
    ):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self._drop_area = QtW.QLabel("Drop here", self)
        self._drop_area.setAlignment(
            Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
        )
        self._drop_area.setFixedHeight(THUMBNAIL_SIZE.height() + 2)
        self._thumbnail = _QImageLabel()
        layout = QtW.QHBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self._thumbnail)
        layout.addWidget(self._drop_area)
        layout.setContentsMargins(0, 0, 0, 0)
        self._allowed_types = types  # the model type
        self._target_id: int | None = None

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
            self.set_subwindow(win)
            self.valueChanged.emit(widget.to_model())

    def set_subwindow(self, src: QSubWindow):
        src_wrapper = _wrapper_for_qwidget(src)
        self._target_id = src_wrapper._identifier
        src_wrapper.closed.connect(self._on_source_closed)
        self._drop_area.setText(src.windowTitle())
        self._drop_area.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        self._thumbnail.set_pixmap(
            src._pixmap_resized(THUMBNAIL_SIZE, QtGui.QColor("#f0f0f0"))
        )

    def widget_for_id(self) -> QSubWindow | None:
        return get_main_window(self).window_for_id(self._target_id)

    def value(self) -> WidgetDataModel | None:
        if widget := self.widget_for_id():
            return widget.to_model()  # TODO: check if this method exists
        return None

    def set_value(self, value: WidgetDataModel | None):
        if value is None:
            self._drop_area.setText("Drop here")
            self._thumbnail.unset_pixmap()
        else:
            raise ValueError("Cannot set WidgetDataModel directly.")

    def _on_source_closed(self):
        self._target_id = None

    def _is_type_maches(self, model_type: str) -> bool:
        if self._allowed_types is None:
            return True
        return any(is_subtype(model_type, t) for t in self._allowed_types)


class QModelDropList(QtW.QListWidget):
    modelsChanged = QtCore.Signal(list)

    def __init__(
        self,
        types: list[str] | None = None,
        parent: QtW.QWidget | None = None,
    ):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self._allowed_types = types  # the model type

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
        event.ignore()
        event.setDropAction(Qt.DropAction.IgnoreAction)

    def dragMoveEvent(self, e: QtGui.QDragMoveEvent):
        e.acceptProposedAction()
        return

    def dropEvent(self, event: QtGui.QDropEvent):
        if isinstance(win := event.source(), QSubWindow):
            self._drop_qsubwindow(win)
        elif isinstance(area := event.source(), QSubWindowArea):
            subwindows = area.subWindowList()
            if len(subwindows) == 1:
                self._drop_qsubwindow(subwindows[0])

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
            self.modelsChanged.emit(self.value())

    def _append_sub_window(self, src: QSubWindow):
        item = QtW.QListWidgetItem()
        self.addItem(item)
        item.setSizeHint(QtCore.QSize(100, THUMBNAIL_SIZE.height() + 2))
        item_widget = QModelListItem(src)
        self.setItemWidget(item, item_widget)
        item_widget.close_requested.connect(self._remove_item)
        win = _wrapper_for_qwidget(src)
        win.closed.connect(lambda: self._remove_item(item_widget))

    def _remove_item(self, item: QModelListItem):
        for i in range(self.count()):
            if self.itemWidget(self.item(i)) is item:
                self.takeItem(i)
                return
        raise ValueError(f"Item {item} not found")

    def value(self) -> list[WidgetDataModel]:
        return [
            self.itemWidget(self.item(i)).widget_for_id().to_model()
            for i in range(self.count())
        ]

    def set_value(self, value: WidgetDataModel | None):
        if value is None:
            self.clear()
        else:
            raise ValueError("Cannot set list of WidgetDataModel directly.")

    if TYPE_CHECKING:

        def itemWidget(self, item: QtW.QListWidgetItem) -> QModelListItem: ...


class QModelListItem(QtW.QWidget):
    close_requested = QtCore.Signal(object)  # emit self

    def __init__(self, src: QSubWindow):
        super().__init__()
        self._thumbnail = _QImageLabel()
        src_wrapper = _wrapper_for_qwidget(src)
        self._thumbnail.set_pixmap(
            src._pixmap_resized(THUMBNAIL_SIZE, QtGui.QColor("#f0f0f0"))
        )
        self._target_id = src_wrapper._identifier
        self._label = QtW.QLabel(src.windowTitle())
        self._label.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        self._close_btn = QtW.QToolButton()
        self._close_btn.setText("✕")
        self._close_btn.setFixedSize(20, 20)
        self._close_btn.clicked.connect(lambda: self.close_requested.emit(self))
        layout = QtW.QHBoxLayout(self)
        layout.addWidget(self._thumbnail)
        layout.addWidget(self._label)
        layout.addWidget(self._close_btn)

    def widget_for_id(self) -> QSubWindow | None:
        return get_main_window(self).window_for_id(self._target_id)

    def enterEvent(self, a0):
        self._close_btn.show()
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


def _wrapper_for_qwidget(src: QSubWindow) -> SubWindow:
    (i_tab, i_src), main = src._find_me_and_main()
    return main.tabs[i_tab][i_src]
