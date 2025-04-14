from __future__ import annotations

from typing import TYPE_CHECKING
import weakref
from qtpy import QtCore, QtWidgets as QtW, QtGui
from app_model.types import Action
from himena.plugins import validate_protocol, update_config_context
from himena_builtins.qt.favorites._config import FavoriteCommandsConfig

if TYPE_CHECKING:
    from himena.widgets import MainWindow


class QFavoriteCommands(QtW.QWidget):
    """List of favorite commands.

    You can add commands to this list from plugin configuration in the setting dialog,
    or directly drag-and-drop commands from the Command History dock widget.
    """

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
            if action := ui.model_app._registered_actions.get(cmd_id):
                self._command_list.add_action(action)


_ID_ROLE = QtCore.Qt.ItemDataRole.UserRole


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
        tooltip = f"{action.tooltip}\n(command ID: {action.id})"
        btn.setToolTip(tooltip)
        item = QtW.QListWidgetItem(self)
        item.setSizeHint(btn.sizeHint())
        item.setData(_ID_ROLE, action.id)
        self.setItemWidget(item, btn)
        btn.delete_requested.connect(lambda: self.delete_item(item))

    def has_action(self, action_id: str) -> bool:
        for i in range(self.count()):
            item = self.item(i)
            if item.data(_ID_ROLE) == action_id:
                return True
        return False

    def delete_item(self, item: QtW.QListWidgetItem):
        """Delete the item from the list."""
        self.takeItem(self.row(item))
        self._update_plugin_config()

    def _update_plugin_config(self):
        with update_config_context(
            config_class=FavoriteCommandsConfig,
            plugin_id="builtins:favorite-commands",
            update_widget=False,
        ) as cfg:
            cfg.commands = [self.item(i).data(_ID_ROLE) for i in range(self.count())]

    def dragEnterEvent(self, e):
        e.accept()
        return super().dragEnterEvent(e)

    def dragMoveEvent(self, e):
        e.accept()
        return super().dragMoveEvent(e)

    def dropEvent(self, e: QtGui.QDropEvent):
        if e.source() is self:
            return super().dropEvent(e)
        self._drop_mime_data(e.mimeData())

    def _drop_mime_data(self, mime: QtCore.QMimeData) -> None:
        """Handle the drop event."""
        if not (ui := self._ui_ref()):
            return
        if mime.hasFormat("text/command-id"):
            command_id = bytes(mime.data("text/command-id")).decode("utf-8")
            if not self.has_action(command_id):
                if action := ui.model_app._registered_actions.get(command_id):
                    self.add_action(action)
                    self._update_plugin_config()


class QCommandPushButton(QtW.QPushButton):
    delete_requested = QtCore.Signal(object)

    def __init__(self, command: str, parent: QtW.QWidget | None = None):
        super().__init__(command, parent)
        self.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        self._command_id = command

    def _make_context_menu(self) -> QtW.QMenu:
        """Create the context menu."""
        menu = QtW.QMenu(self)
        action = menu.addAction("Delete")
        action.triggered.connect(lambda: self.delete_requested.emit(self))
        return menu

    def _show_context_menu(self, pos: QtCore.QPoint):
        """Show the context menu."""
        self._make_context_menu().exec(self.mapToGlobal(pos))


def _make_callback(ui: MainWindow, cmd: str):
    """Create a callback for the command."""

    def callback():
        ui.exec_action(cmd)

    return callback
