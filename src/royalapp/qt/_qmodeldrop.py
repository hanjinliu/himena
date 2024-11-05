from __future__ import annotations
from typing import Hashable
from logging import getLogger
from qtpy import QtWidgets as QtW, QtCore, QtGui
from royalapp.types import WidgetDataModel
from royalapp.qt._qsub_window import QSubWindow
from royalapp.qt._utils import get_main_window

_LOGGER = getLogger(__name__)


class QModelDrop(QtW.QWidget):
    """Widget for dropping model data from a subwindow."""

    valueChanged = QtCore.Signal(WidgetDataModel)

    def __init__(
        self,
        types: list[Hashable] | None = None,
        parent: QtW.QWidget | None = None,
    ):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self._drop_area = QtW.QLabel("Drop here", self)
        self._drop_area.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignCenter | QtCore.Qt.AlignmentFlag.AlignVCenter
        )
        self._drop_area.setFixedHeight(THUMBNAIL_SIZE.height())
        self._thumbnail = _QImageLabel()
        layout = QtW.QHBoxLayout(self)
        layout.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter
        )
        layout.addWidget(self._thumbnail)
        layout.addWidget(self._drop_area)
        layout.setContentsMargins(0, 0, 0, 0)
        self._allowed_types = types  # the model type
        self._target_id: int | None = None

    def dragEnterEvent(self, event: QtGui.QDragEnterEvent):
        if isinstance(src := event.source(), QSubWindow):
            widget = src.main_widget()
            if not hasattr(widget, "to_model"):
                _LOGGER.debug("Ignoring drop event")
                event.ignore()
                event.setDropAction(QtCore.Qt.DropAction.IgnoreAction)
                return
            model_type = getattr(widget, "model_type", lambda: None)()
            _LOGGER.info("Entered model type %s", model_type)
            if self._is_type_maches(model_type):
                _LOGGER.debug("Accepting drop event")
                event.accept()
                return
        event.ignore()
        event.setDropAction(QtCore.Qt.DropAction.IgnoreAction)

    def dropEvent(self, event: QtGui.QDropEvent):
        if isinstance(src := event.source(), QSubWindow):
            widget = src.main_widget()
            model_type = getattr(widget, "model_type", lambda: None)()
            _LOGGER.info("Dropped model type %s", model_type)
            if self._is_type_maches(model_type):
                (i_tab, i_src), main = src._find_me_and_main()
                src_wrapper = main.tabs[i_tab][i_src]
                self._target_id = src_wrapper._identifier
                src_wrapper.closed.connect(self._on_source_closed)
                _LOGGER.info("Dropped model %s", src.windowTitle())
                self.set_subwindow(src)
                self.valueChanged.emit(widget.to_model())

    def set_subwindow(self, src: QSubWindow):
        (i_tab, i_src), main = src._find_me_and_main()
        src_wrapper = main.tabs[i_tab][i_src]
        self._target_id = src_wrapper._identifier
        src_wrapper.closed.connect(self._on_source_closed)
        self._drop_area.setText(src.windowTitle())
        self._drop_area.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter
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
        raise NotImplementedError

    def _on_source_closed(self):
        self._target_id = None

    def _is_type_maches(self, model_type: Hashable) -> bool:
        if self._allowed_types is None:
            return True
        return any(hash(model_type) == hash(t) for t in self._allowed_types)


THUMBNAIL_SIZE = QtCore.QSize(50, 50)


class _QImageLabel(QtW.QLabel):
    def __init__(self):
        super().__init__()
        self.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignCenter | QtCore.Qt.AlignmentFlag.AlignTop
        )
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
                QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                QtCore.Qt.TransformationMode.SmoothTransformation,
            )
        )

    def unset_pixmap(self):
        self.setFixedSize(0, 0)
        self.clear()
