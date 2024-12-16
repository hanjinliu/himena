from __future__ import annotations

from typing import TYPE_CHECKING
import logging
import weakref
from app_model import Action
from qtpy import QtWidgets as QtW, QtCore, QtGui
from qtpy.QtCore import Qt
from superqt import QIconifyIcon

from himena._utils import lru_cache

if TYPE_CHECKING:
    from himena.widgets import MainWindow

_LOGGER = logging.getLogger(__name__)


class QCommandHistory(QtW.QWidget):
    def __init__(self, ui: MainWindow):
        super().__init__()
        layout = QtW.QVBoxLayout(self)
        self._command_list = QCommandList(ui)
        layout.addWidget(self._command_list)
        ui.model_app.commands.executed.connect(self._command_executed)
        self._ui_ref = weakref.ref(ui)
        self._command_list._update_index_widgets()

    def _command_executed(self, command_id: str) -> None:
        _LOGGER.info("Command executed: %s", command_id)
        num = len(self._ui_ref()._history_command)
        self._command_list.model().beginInsertRows(
            QtCore.QModelIndex(), num - 1, num - 1
        )
        self._command_list.model().insertRow(num - 1, QtCore.QModelIndex())
        self._command_list._update_index_widgets()
        self._command_list.model().endInsertRows()


class QCommandList(QtW.QListView):
    current_index_changed = QtCore.Signal(int)

    def __init__(self, ui: MainWindow, parent: QtW.QWidget | None = None) -> None:
        super().__init__(parent)
        model = QCommandListModel(ui)
        self.setModel(model)
        self.setEditTriggers(QtW.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setSelectionMode(QtW.QAbstractItemView.SelectionMode.SingleSelection)

    def model(self) -> QCommandListModel:
        return super().model()

    def currentChanged(
        self, current: QtCore.QModelIndex, previous: QtCore.QModelIndex
    ) -> None:
        super().currentChanged(current, previous)
        row = current.row()
        if row >= 0:
            self.current_index_changed.emit(row)

    def _update_index_widgets(self):
        for row in range(self.model().rowCount()):
            index = self.model().index(row)
            if not index.isValid():
                return None
            if action := self.model()._action_at(row):
                id = action.id
                title = action.title
            else:
                id = ""
                title = ""
            if widget := self.indexWidget(index):
                widget.setText(title)
            else:
                widget = QCommandIndexWidget(id, title, self)
                self.setIndexWidget(index, widget)
                widget.btn_clicked.connect(self._execute_action_at_widget)

    def _find_index_widget(
        self, widget: QCommandIndexWidget
    ) -> QtCore.QModelIndex | None:
        for row in range(self.model().rowCount()):
            index = self.model().index(row)
            if self.indexWidget(index) == widget:
                if not index.isValid():
                    return None
                return index

    def _execute_action_at_widget(self, widget: QCommandIndexWidget):
        index = self._find_index_widget(widget)
        if index is None:
            return
        if action := self.model()._action_at(index.row()):
            if ui := self.model()._ui_ref():
                ui.exec_action(action.id)

    if TYPE_CHECKING:

        def indexWidget(
            self, index: QtCore.QModelIndex
        ) -> QCommandIndexWidget | None: ...


def _color(light_background: bool):
    if light_background:
        color = "#222222"
    else:
        color = "#E6E6E6"
    return color


@lru_cache(maxsize=1)
def _icon_run(light_background: bool) -> QIconifyIcon:
    return QIconifyIcon("fa:play", color=_color(light_background))


@lru_cache(maxsize=1)
def _icon_copy(light_background: bool) -> QIconifyIcon:
    return QIconifyIcon(
        "heroicons-outline:clipboard-copy", color=_color(light_background)
    )


def make_btn(tooltip: str):
    btn = QtW.QToolButton()
    btn.setObjectName("QCommandHistory-RunButton")
    btn.setIcon(QtGui.QIcon())
    btn.setFixedWidth(20)
    btn.setToolTip(tooltip)
    return btn


class QCommandIndexWidget(QtW.QWidget):
    btn_clicked = QtCore.Signal(object)

    def __init__(self, id: str, text: str, listwidget: QCommandList):
        super().__init__()
        self._action_id = id
        layout = QtW.QHBoxLayout(self)
        layout.setContentsMargins(5, 0, 0, 0)
        layout.setSpacing(0)
        self._label = QtW.QLabel(text)
        self._btn_run = make_btn("Run this command")
        self._btn_copy = make_btn("Copy this command ID")
        layout.addWidget(self._label, stretch=100, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self._btn_copy, alignment=Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self._btn_run, alignment=Qt.AlignmentFlag.AlignRight)
        self.setMouseTracking(True)
        self._listwidget_ref = weakref.ref(listwidget)
        self._btn_run.clicked.connect(self._emit_run_clicked)
        self._btn_copy.clicked.connect(self._emit_copy_clicked)

    def setText(self, text: str):
        self._label.setText(text)

    def _emit_run_clicked(self):
        self.btn_clicked.emit(self)

    def _emit_copy_clicked(self):
        if self._action_id and (clipboard := QtW.QApplication.clipboard()):
            clipboard.setText(self._action_id)

    def _is_light_background(self) -> bool:
        try:
            return self._listwidget_ref().model()._ui_ref().theme.is_light_background()
        except Exception:
            return False

    def set_button_visible(self, visible: bool):
        self._btn_run.setEnabled(visible)
        if visible:
            light_bg = self._is_light_background()
            self._btn_run.setIcon(QtGui.QIcon(_icon_run(light_bg)))
            self._btn_copy.setIcon(QtGui.QIcon(_icon_copy(light_bg)))
            self._btn_run.setCursor(Qt.CursorShape.PointingHandCursor)
            self._btn_copy.setCursor(Qt.CursorShape.PointingHandCursor)
        else:
            self._btn_run.setIcon(QtGui.QIcon())
            self._btn_copy.setIcon(QtGui.QIcon())
            self._btn_run.setCursor(Qt.CursorShape.ArrowCursor)
            self._btn_copy.setCursor(Qt.CursorShape.ArrowCursor)

    def enterEvent(self, event: QtCore.QEvent) -> None:
        listwidget = self._listwidget_ref()
        if listwidget is None:
            return super().enterEvent(event)
        ui = listwidget.model()._ui_ref()
        index = listwidget._find_index_widget(self)
        action = listwidget.model()._action_at(index.row())
        if ui is None or action is None:
            return super().enterEvent(event)
        # check enablement
        if action.enablement is None:
            enabled = True
        else:
            ctx = ui._ctx_keys.dict()
            enabled = action.enablement.eval(ctx)
        self.set_button_visible(enabled)
        return super().enterEvent(event)

    def leaveEvent(self, event: QtCore.QEvent) -> None:
        self.set_button_visible(False)
        return super().leaveEvent(event)


class QCommandListModel(QtCore.QAbstractListModel):
    def __init__(self, ui: MainWindow, parent=None):
        super().__init__(parent)
        self._ui_ref = weakref.ref(ui)

    def rowCount(self, parent=None):
        if ui := self._ui_ref():
            return ui._history_command.len()
        return 0

    def _action_at(self, row: int) -> Action | None:
        """app-model Action at the given row."""
        if ui := self._ui_ref():
            command_id = ui._history_command.get(row)
            if command_id is None:
                return None
            return ui.model_app._registered_actions.get(command_id)
        return None

    def data(self, index, role):
        if not index.isValid():
            return QtCore.QVariant()
        if role == Qt.ItemDataRole.ToolTipRole:
            if action := self._action_at(index.row()):
                return action.tooltip
        elif role == Qt.ItemDataRole.StatusTipRole:
            if action := self._action_at(index.row()):
                return action.status_tip
        elif role == Qt.ItemDataRole.DisplayRole:
            return ""
        return QtCore.QVariant()
