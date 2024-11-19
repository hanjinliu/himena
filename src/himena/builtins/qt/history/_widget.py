from __future__ import annotations

from typing import TYPE_CHECKING
import weakref
from app_model import Action
from qtpy import QtWidgets as QtW, QtCore, QtGui
from qtpy.QtCore import Qt
from superqt import QIconifyIcon

from himena._utils import lru_cache

if TYPE_CHECKING:
    from himena.widgets import MainWindow


class QCommandHistory(QtW.QWidget):
    def __init__(self, ui: MainWindow):
        super().__init__()
        layout = QtW.QVBoxLayout(self)
        self._command_list = QCommandList(ui)
        layout.addWidget(self._command_list)
        ui.model_app.commands.executed.connect(self._command_executed)
        self._ui_ref = weakref.ref(ui)

    def _command_executed(self, command_id: str) -> None:
        num = len(self._ui_ref()._history_command)
        self._command_list.model().beginInsertRows(QtCore.QModelIndex(), 0, num - 1)
        self.update()
        self._command_list.model().endInsertRows()
        self._command_list._update_index_widgets()


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
            if action := self.model()._action_at(row):
                title = action.title
            else:
                title = ""
            if widget := self.indexWidget(index):
                widget.setText(title)
            else:
                widget = QCommandIndexWidget(title, self)
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


@lru_cache(maxsize=1)
def _icon_run(light_background: bool) -> QIconifyIcon:
    if light_background:
        color = "#222222"
    else:
        color = "#E6E6E6"
    return QIconifyIcon("fa:play", color=color)


class QCommandIndexWidget(QtW.QWidget):
    btn_clicked = QtCore.Signal(object)

    def __init__(self, text: str, listwidget: QCommandList):
        super().__init__()
        layout = QtW.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._label = QtW.QLabel(text)
        self._button = QtW.QToolButton()
        self._button.setObjectName("QCommandHistory-RunButton")
        self._button.setIcon(QtGui.QIcon())
        self._button.setFixedWidth(20)
        layout.addWidget(self._button)
        layout.addWidget(self._label)
        self.setMouseTracking(True)
        self._listwidget_ref = weakref.ref(listwidget)

    def setText(self, text: str):
        self._label.setText(text)

    def set_button_visible(self, visible: bool):
        self._button.setEnabled(visible)
        if visible:
            self._button.setIcon(QtGui.QIcon(_icon_run(True)))
            self._button.setCursor(Qt.CursorShape.PointingHandCursor)
        else:
            self._button.setIcon(QtGui.QIcon())
            self._button.setCursor(Qt.CursorShape.ArrowCursor)

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
            return None
        if role == Qt.ItemDataRole.ToolTipRole:
            if action := self._action_at(index.row()):
                return action.tooltip
        elif role == Qt.ItemDataRole.StatusTipRole:
            if action := self._action_at(index.row()):
                return action.status_tip

        return None
