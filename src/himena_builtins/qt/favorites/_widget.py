from __future__ import annotations

from typing import TYPE_CHECKING
import weakref
from qtpy import QtCore, QtWidgets as QtW
from app_model.types import Action
from himena.plugins import validate_protocol

if TYPE_CHECKING:
    from himena.widgets import MainWindow
    from himena_builtins.qt.favorites import FavoriteCommandsConfig


class QFavoriteCommands(QtW.QWidget):
    def __init__(self, ui: MainWindow):
        super().__init__()
        self._ui_ref = weakref.ref(ui)
        self._command_list = QCommandList(self)
        layout = QtW.QVBoxLayout(self)

        layout.addWidget(self._command_list)

    @validate_protocol
    def update_configs(self, cfg: FavoriteCommandsConfig) -> None:
        if not (ui := self._ui_ref()):
            return
        self._command_list.clear()
        for cmd_id in cfg.commands:
            try:
                action = ui.model_app.commands[cmd_id]
            except KeyError:
                continue
            self._command_list.add_action(action)


class QCommandList(QtW.QListWidget):
    def __init__(self, parent: QFavoriteCommands):
        super().__init__(parent)
        self._ui_ref = parent._ui_ref
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDefaultDropAction(QtCore.Qt.DropAction.MoveAction)
        self.setSelectionMode(QtW.QAbstractItemView.SelectionMode.SingleSelection)
        self.setDragDropMode(QtW.QAbstractItemView.DragDropMode.InternalMove)

    def add_action(self, action: Action):
        btn = QCommandPushButton(action.title)
        btn.clicked.connect(_make_callback(self._ui_ref(), action.id))
        btn.setToolTip(action.id)
        item = QtW.QListWidgetItem(self)
        item.setData(QtCore.Qt.ItemDataRole.UserRole, action.id)
        self.setItemWidget(item, btn)


class QCommandPushButton(QtW.QPushButton):
    delete_requested = QtCore.Signal(object)

    def __init__(self, command: str, parent: QtW.QWidget | None = None):
        super().__init__(command, parent)
        self.button = QtW.QPushButton(command, self)
        self.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        self._command_id = command

    def _show_context_menu(self, pos: QtCore.QPoint):
        """Show the context menu."""
        menu = QtW.QMenu(self)
        action = menu.addAction("Delete")
        action.triggered.connect(lambda: self.delete_requested.emit(self))
        menu.exec(self.mapToGlobal(pos))


def _make_callback(ui: MainWindow, cmd: str):
    """Create a callback for the command."""

    def callback():
        ui.exec_action(cmd)

    return callback
