from __future__ import annotations
from typing import Hashable
from logging import getLogger
from qtpy import QtWidgets as QtW, QtCore, QtGui
from royalapp.types import WidgetDataModel
from royalapp.qt._qsub_window import QSubWindow
from royalapp.qt._utils import get_main_window
from royalapp.qt.registry import type_for_widget

_LOGGER = getLogger(__name__)


class QModelDrop(QtW.QWidget):
    """Widget for dropping model data from a subwindow."""

    valueChanged = QtCore.Signal(WidgetDataModel)

    def __init__(self, type: Hashable, parent: QtW.QWidget | None = None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self._drop_area = QtW.QLabel("Drop here", self)
        self._drop_area.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        layout = QtW.QHBoxLayout(self)
        layout.addWidget(self._drop_area)
        self._type = type  # the model type
        self._target_id: int | None = None

    def dragEnterEvent(self, event: QtGui.QDragEnterEvent):
        if isinstance(src := event.source(), QSubWindow):
            model_type = type_for_widget(src)
            if hash(model_type) == hash(self._type):
                _LOGGER.debug("Accepting drop event")
                event.accept()
                return
        event.ignore()

    def dropEvent(self, event: QtGui.QDropEvent):
        if isinstance(src := event.source(), QSubWindow):
            model_type = type_for_widget(src)
            if hash(model_type) == hash(self._type):
                (i_tab, i_src), main = src._find_me_and_main()
                src_wrapper = main.tabs[i_tab][i_src]
                self._target_id = src_wrapper._identifier
                src_wrapper.closed.connect(self._on_source_closed)

    def set_subwindow(self, src: QSubWindow):
        (i_tab, i_src), main = src._find_me_and_main()
        src_wrapper = main.tabs[i_tab][i_src]
        self._target_id = src_wrapper._identifier
        src_wrapper.closed.connect(self._on_source_closed)
        self._drop_area.setText(src._title_bar._title_label.text())
        # self.valueChanged.emit(src.to_model())  # NOTE: maybe time consuming

    def widget_for_id(self) -> QSubWindow | None:
        return get_main_window(self).widget_for_id(self._target_id)

    def value(self) -> WidgetDataModel | None:
        if widget := self.widget_for_id():
            return widget.to_model()  # TODO: check if this method exists
        return None

    def set_value(self, value: WidgetDataModel | None):
        raise NotImplementedError

    def _on_source_closed(self):
        self._target_id = None
