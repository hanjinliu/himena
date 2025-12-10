from __future__ import annotations

from typing import TYPE_CHECKING, Iterable, Iterator
from logging import getLogger
from contextlib import contextmanager, suppress
from concurrent.futures import Future, ThreadPoolExecutor
import warnings
from qtpy import QtWidgets as QtW, QtCore, QtGui
from qtpy.QtCore import Qt
from app_model.types import KeyBindingRule, KeyBinding, SimpleKeyBinding
from app_model.backends.qt import QCommandAction, QModelMenu, QKeyBindingSequence
from superqt import ensure_main_thread

from himena.consts import MonospaceFontFamily

if TYPE_CHECKING:
    from himena._app_model import HimenaApplication
    from himena.qt.main_window import MainWindowQt

_EXECUTOR = ThreadPoolExecutor()
_LOGGER = getLogger(__name__)


class H:
    TITLE = 0
    KEYBINDING = 1
    WHEN = 2
    SOURCE = 3
    COMMAND_ID = 4
    WEIGHT = 5


class QKeybindEdit(QtW.QWidget):
    """Widget for editing keybindings."""

    def __init__(self, ui: MainWindowQt):
        super().__init__()
        self._ui = ui
        layout = QtW.QVBoxLayout(self)
        self._search = QKeybindSearch(self)
        layout.addWidget(self._search)
        self._table = QKeybindTable(ui.model_app, self)
        layout.addWidget(self._table)
        self._table.update_table_from_model_app(ui.model_app)
        self._restore_default_btn = QtW.QPushButton("Restore")
        self._restore_default_btn.setToolTip("Restore the default keybindings.")
        self._restore_default_btn.setFixedWidth(84)
        self._restore_default_btn.clicked.connect(self._restore_default)
        layout.addWidget(
            self._restore_default_btn, alignment=Qt.AlignmentFlag.AlignRight
        )
        self._search.textChanged.connect(self._on_search_text_changed)
        self._table.keybinding_updated.connect(self._on_keybinding_updated)

    def _on_search_text_changed(self, text: str):
        self._table.filter_by_text_async(text)

    def _on_keybinding_updated(self, command_id: str, new_shortcut: str):
        _LOGGER.info("Keybindings registered: %s -> %s", command_id, new_shortcut)
        self._table.update_table_from_model_app(self._ui.model_app)
        self._table.filter_by_text(self._search.text())  # re-filter
        self._ui.app_profile.with_keybinding_override(new_shortcut, command_id).save()
        _LOGGER.info("Keybinding override saved")
        qui = self._ui._backend_main_window
        for qa in _iter_command_action(qui._menubar.actions() + qui._toolbar.actions()):
            if qa._command_id == command_id:
                parts = [
                    SimpleKeyBinding.from_str(part) for part in new_shortcut.split(", ")
                ]
                qa.setShortcut(QKeyBindingSequence(KeyBinding(parts=parts)))

    def _restore_default(self):
        _LOGGER.info("Restoring keybindings.")
        qui = self._ui._backend_main_window
        app = self._ui.model_app
        for ko in self._ui.app_profile.keybinding_overrides:
            keybind = app.keybindings.get_keybinding(ko.command_id)
            if keybind:
                app.keybindings._keymap.pop(keybind.keybinding.to_int(), -1)
        self._ui.app_profile.keybinding_overrides.clear()
        self._ui.app_profile.save()
        for qa in _iter_command_action(qui._menubar.actions() + qui._toolbar.actions()):
            if action := self._ui.model_app.registered_actions.get(qa._command_id):
                if action.keybindings:
                    for kb in action.keybindings:
                        if kb.primary:
                            app.keybindings.register_keybinding_rule(
                                action.id, KeyBindingRule(primary=kb.primary)
                            )
                            kb_obj = app.keybindings.get_keybinding(
                                action.id
                            ).keybinding
                            qa.setShortcut(QKeyBindingSequence(kb_obj))
        self._table.update_table_from_model_app(self._ui.model_app)
        self._table.filter_by_text(self._search.text())  # re-filter


class QKeybindSearch(QtW.QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setPlaceholderText("Type to Search keybindings...")
        self.setToolTip(
            "Search keybindings by command title, keybinding, or command ID."
        )


class QKeybindTable(QtW.QTableWidget):
    keybinding_updated = QtCore.Signal(str, str)  # command_id, new_keybinding

    def __init__(self, app: HimenaApplication, parent=None):
        super().__init__(parent)
        self._app = app
        self.setColumnCount(5)
        self.setSelectionBehavior(QtW.QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QtW.QAbstractItemView.SelectionMode.SingleSelection)

        # Design and UX
        self.setShowGrid(False)
        self.horizontalHeader().setStretchLastSection(True)
        self.setHorizontalHeaderLabels(
            ["Command", "Keybinding", "When", "Source", "ID", "Weight"]
        )
        self.verticalHeader().setVisible(False)
        self._default_row_height = 22
        self.horizontalHeader().setFixedHeight(self._default_row_height)
        self.setVerticalScrollMode(QtW.QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.setHorizontalScrollMode(QtW.QAbstractItemView.ScrollMode.ScrollPerPixel)

        # Hide "weight" for now, but may be useful in the future
        self.setColumnHidden(H.WEIGHT, True)

        self.setItemDelegateForColumn(H.KEYBINDING, QKeybindDelegate(self))
        self.setColumnWidth(H.TITLE, 210)
        self.setColumnWidth(H.KEYBINDING, 120)
        self.setColumnWidth(H.WHEN, 120)
        self.setColumnWidth(H.WEIGHT, 40)
        self.setColumnWidth(H.SOURCE, 60)
        self.setColumnWidth(H.COMMAND_ID, 180)

        self._update_blocked = False
        self._last_future: Future | None = None
        self.cellChanged.connect(self._update_keybinding)

    def update_table_from_model_app(self, app: HimenaApplication):
        commands_to_skip = app._dynamic_command_ids
        commands = sorted(
            (cmd[1] for cmd in app.commands if cmd[1].id not in commands_to_skip),
            key=lambda cmd: cmd.title,
        )
        with self.block_context():
            self.clearContents()
            self.setRowCount(len(commands))
            for i, cmd in enumerate(commands):
                self.setRowHeight(i, self._default_row_height)
                cmd_id = cmd.id
                if ":" in cmd_id:
                    source = cmd_id.split(":", maxsplit=1)[0]
                else:
                    source = ""
                title = cmd.title
                kbd = app.keybindings.get_keybinding(cmd_id)
                if kbd:
                    key_seq = kbd.keybinding.to_text()
                    when = str(kbd.when) if kbd.when is not None else ""
                    # weight = str(kbd.weight)
                else:
                    key_seq = ""
                    when = ""
                    # weight = ""
                if action := app.registered_actions.get(cmd_id):
                    tooltip = action.tooltip
                else:
                    tooltip = None
                if tooltip:
                    tooltip = title + "\n" + tooltip
                self.setItem(i, H.TITLE, _item_basic(title, tooltip=tooltip))
                self.setItem(i, H.KEYBINDING, QtW.QTableWidgetItem(key_seq))
                self.setItem(i, H.WHEN, _item_basic(when, monospace=True))
                # self.setItem(i, H.WEIGHT, _item_basic(weight))  # hide for now
                self.setItem(i, H.SOURCE, _item_basic(source))
                self.setItem(i, H.COMMAND_ID, _item_basic(cmd_id, monospace=True))

    def filter_by_text(self, text: str) -> list[bool] | None:
        text = text.lower().strip()

        # disable filtering if text is empty
        if text == "":
            return None

        parts = text.split(" ")
        out = []
        for row in range(self.rowCount()):
            kb = self.item(row, H.KEYBINDING).text().lower()
            title = self.item(row, H.TITLE).text().lower()
            id = self.item(row, H.COMMAND_ID).text().lower()
            if (
                kb
                and any(part in kb for part in parts)
                or title
                and any(part in title for part in parts)
                or id
                and any(part in id for part in parts)
            ):
                out.append(True)
            else:
                out.append(False)
        return out

    def filter_by_text_async(self, text: str) -> Future:
        if self._last_future:
            self._last_future.cancel()
        future = _EXECUTOR.submit(self.filter_by_text, text)
        self._last_future = future
        future.add_done_callback(self._filter_done)
        return future

    @ensure_main_thread
    def _filter_done(self, future: Future):
        if future.cancelled():
            return
        result = future.result()
        self._last_future = None
        with suppress(RuntimeError):
            # this function may be called after the widget is destroyed
            if result is not None:
                for i, show in enumerate(result):
                    self.setRowHidden(i, not show)
            else:
                for i in range(self.rowCount()):
                    self.setRowHidden(i, False)

    @contextmanager
    def block_context(self):
        was_blocked = self._update_blocked
        self._update_blocked = True
        try:
            yield
        finally:
            self._update_blocked = was_blocked

    def _update_keybinding(self, row: int, col: int):
        if col != H.KEYBINDING or self._update_blocked or row < 0:
            return
        self.setCurrentItem(self.item(row, col))
        current_item = self.currentItem()
        if current_item is None:
            return
        new_shortcut = current_item.text()
        command_id = self.item(row, H.COMMAND_ID).text()
        kbd_current = self._app.keybindings.get_keybinding(command_id)
        if kbd_current is None or kbd_current.keybinding.to_text() != new_shortcut:
            conflictions = self._get_confliction_command_ids(new_shortcut, command_id)
            if conflictions:
                warnings.warn(
                    f"Keybinding {new_shortcut} probably conflicts with the following "
                    f"commands: {conflictions}",
                    RuntimeWarning,
                    stacklevel=2,
                )
            if kbd_current is not None:
                self._app.keybindings._keymap.pop(kbd_current.keybinding.to_int(), -1)
            if new_shortcut:
                kb = KeyBindingRule(primary=new_shortcut.replace(", ", " "))
                self._app.keybindings.register_keybinding_rule(command_id, kb)
            self.keybinding_updated.emit(command_id, new_shortcut)

    def _get_confliction_command_ids(
        self, keybinding: str, except_for: str
    ) -> list[str]:
        conflictions: list[str] = []
        for kbd in self._app.keybindings:
            if kbd.command_id == except_for:
                continue
            if kbd.keybinding.to_text() == keybinding:
                # TODO: check "when" to avoid adding conflictions of independent
                # keybindings.
                conflictions.append(kbd.command_id)
        return conflictions


def _item_basic(
    text: str,
    monospace: bool = False,
    tooltip: str | None = None,
) -> QtW.QTableWidgetItem:
    item = QtW.QTableWidgetItem(text)
    if tooltip is None:
        tooltip = text
    item.setToolTip(tooltip)
    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
    if monospace:
        item.setFont(QtGui.QFont(MonospaceFontFamily))
    return item


class QKeybindDelegate(QtW.QItemDelegate):
    """Delegate that handles when user types in new shortcut."""

    def createEditor(self, widget, style_option, model_index: QtCore.QModelIndex):
        if model_index.isValid():
            self._editor = QKeybindingLineEdit(widget)
            return self._editor

    def setEditorData(
        self, widget: QKeybindingLineEdit, model_index: QtCore.QModelIndex
    ):
        if model_index.isValid():
            text = widget.keySequence().toString()
            widget.setKeySequence(text)

    def updateEditorGeometry(
        self,
        widget: QKeybindingLineEdit,
        style_option: QtW.QStyleOptionViewItem,
        model_index: QtCore.QModelIndex,
    ):
        if model_index.isValid():
            widget.setGeometry(style_option.rect)

    def setModelData(
        self,
        widget: QKeybindingLineEdit,
        abstract_item_model: QtCore.QAbstractItemModel,
        model_index: QtCore.QModelIndex,
    ):
        if model_index.isValid():
            text = widget.keySequence().toString()
            abstract_item_model.setData(model_index, text, Qt.ItemDataRole.EditRole)


class QKeybindingLineEdit(QtW.QKeySequenceEdit):
    """Widget used to edit keybindings."""


def _find_action(
    actions: Iterable[QtW.QAction], command_id: str
) -> Iterator[QCommandAction]:
    """Yield all actions with the given command ID."""
    for action in actions:
        if isinstance(action, QCommandAction):
            if action._command_id == command_id:
                yield action
            elif menu := action.menu():
                yield from _find_action(menu.actions(), command_id)
        elif isinstance(menu := action.menu(), QModelMenu):
            yield from _find_action(menu.actions(), command_id)


def _iter_command_action(actions: Iterable[QtW.QAction]) -> Iterator[QCommandAction]:
    for action in actions:
        if isinstance(action, QCommandAction):
            yield action
        elif isinstance(menu := action.menu(), QModelMenu):
            yield from _iter_command_action(menu.actions())
