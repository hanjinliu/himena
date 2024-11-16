from __future__ import annotations

from typing import TYPE_CHECKING
import weakref
from app_model import Action
from qtpy import QtWidgets as QtW, QtCore
from qtpy.QtCore import Qt

if TYPE_CHECKING:
    from himena.widgets import MainWindow


class QCommandHistory(QtW.QWidget):
    def __init__(self, ui: MainWindow):
        super().__init__()
        layout = QtW.QVBoxLayout(self)
        self._command_list = QCommandList(ui)
        layout.addWidget(self._command_list)
        self._execute_button = QtW.QPushButton("Execute")
        self._execute_button.clicked.connect(self._execute)
        self._execute_button.setEnabled(False)
        layout.addWidget(self._execute_button)

        ui.model_app.commands.executed.connect(self._command_executed)
        self._command_list.current_index_changed.connect(self._current_changed)
        self._ui_ref = weakref.ref(ui)

    def _command_executed(self, command_id: str) -> None:
        self._command_list.model().beginInsertRows(QtCore.QModelIndex(), 0, 0)
        self.update()
        self._command_list.model().endInsertRows()

    def _execute(self) -> None:
        if action := self._command_list._current_action():
            if ui := self._ui_ref():
                ui.exec_action(action.id)

    def _current_changed(self, row: int):
        ui = self._ui_ref()
        if ui is None:
            return
        if action := self._command_list.model()._action_at(row):
            if action.enablement is None:
                self._execute_button.setEnabled(True)
            else:
                ctx = ui._ctx_keys.dict()
                self._execute_button.setEnabled(action.enablement.eval(ctx))
        else:
            self._execute_button.setEnabled(False)


class QCommandList(QtW.QListView):
    current_index_changed = QtCore.Signal(int)

    def __init__(self, ui: MainWindow, parent: QtW.QWidget | None = None) -> None:
        super().__init__(parent)
        model = QCommandListModel(ui)
        self.setModel(model)
        self.setEditTriggers(QtW.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setSelectionMode(QtW.QAbstractItemView.SelectionMode.SingleSelection)

    def _current_action(self) -> Action | None:
        index = self.currentIndex()
        return self.model()._action_at(index.row()) if index.isValid() else None

    def model(self) -> QCommandListModel:
        return super().model()

    def currentChanged(
        self, current: QtCore.QModelIndex, previous: QtCore.QModelIndex
    ) -> None:
        super().currentChanged(current, previous)
        row = current.row()
        if row >= 0:
            self.current_index_changed.emit(row)


class QCommandListModel(QtCore.QAbstractListModel):
    def __init__(self, ui: MainWindow, parent=None):
        super().__init__(parent)
        self._ui_ref = weakref.ref(ui)

    def rowCount(self, parent):
        if ui := self._ui_ref():
            return ui._history_command.count()
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
            return None
        if role == Qt.ItemDataRole.DisplayRole:
            if action := self._action_at(index.row()):
                return action.title
        elif role == Qt.ItemDataRole.ToolTipRole:
            if action := self._action_at(index.row()):
                return action.tooltip
        elif role == Qt.ItemDataRole.StatusTipRole:
            if action := self._action_at(index.row()):
                return action.status_tip

        return None
