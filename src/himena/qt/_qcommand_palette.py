from __future__ import annotations

import re
import logging
from collections.abc import Iterator, Mapping
from typing import TYPE_CHECKING, Any, Iterable, cast, Callable

from app_model import Application
from app_model.types import CommandRule, MenuItem, Action
from qtpy import QtCore, QtGui, QtWidgets as QtW
from qtpy.QtCore import Qt, Signal

if TYPE_CHECKING:
    from himena.qt.main_window import QMainWindow
    from app_model.types import MenuOrSubmenu

_LOGGER = logging.getLogger(__name__)


def _collect_command(
    app: Application,
    menu_items: list[MenuOrSubmenu],
    exclude: Iterable[str],
) -> list[Action]:
    commands = []
    for item in menu_items:
        if isinstance(item, MenuItem):
            if item.command.id not in exclude:
                commands.append(item.command)
        else:
            commands.extend(
                _collect_command(app, app.menus.get_menu(item.submenu), exclude)
            )
    return commands


class QCommandPalette(QtW.QWidget):
    """A Qt command palette widget."""

    def __init__(
        self,
        app: Application,
        menu_id: str | None = None,
        parent: QtW.QWidget | None = None,
        exclude: Iterable[str] = (),
        formatter: Callable[[Action], str] = lambda x: x.title,
        placeholder: str = "Search commands by name ...",
    ):
        super().__init__(parent)

        self._line = QCommandLineEdit()
        self._line.setPlaceholderText(placeholder)
        self._list = QCommandList(self, formatter)
        _layout = QtW.QVBoxLayout(self)
        _layout.addWidget(self._line)
        _layout.addWidget(self._list)
        self.setLayout(_layout)

        self._line.textChanged.connect(self._on_text_changed)
        self._list.commandClicked.connect(self._on_command_clicked)
        self._line.editingFinished.connect(self.hide)
        font = self.font()
        font.setPointSize(14)
        self.setFont(font)
        self._line.setFont(font)
        font = self._list.font()
        font.setPointSize(11)
        self._list.setFont(font)
        self.hide()
        self._menu_id = menu_id or app.menus.COMMAND_PALETTE_ID
        self._exclude = set(exclude)
        self._command_initialized = False

        app.menus.menus_changed.connect(self._on_app_menus_changed)
        self._model_app = app
        self._need_update = False  # needs update before showing the palette

    def _initialize_commands(self) -> None:
        app = self._model_app
        try:
            menu_items = app.menus.get_menu(self._menu_id)
            commands = _collect_command(app, menu_items, self._exclude)
            self.extend_command(commands)
        except KeyError:
            pass
        _LOGGER.info("Command palette initialized.")
        self._command_initialized = True

    def sizeHint(self) -> QtCore.QSize:
        return QtCore.QSize(600, 400)

    def extend_command(self, list_of_commands: Iterable[CommandRule]) -> None:
        self._list.extend_command(list_of_commands)
        return

    def _on_text_changed(self, text: str) -> None:
        self._list.update_for_text(text)
        return

    def _on_command_clicked(self, index: int) -> None:
        index_widget = self._list.widget_at(index)
        if index_widget.disabled():
            return
        self._list.execute(index)
        self.hide()
        return

    def _on_app_menus_changed(self, changed_menus: set[str]) -> None:
        """Connected to app_model.menus.menus_changed."""
        if self._menu_id not in changed_menus:
            return
        self._need_update = True

    def _update_contents(self) -> None:
        app = self._model_app
        all_cmds_set = set(self._list.all_commands)
        try:
            menus = app.menus.get_menu(self._menu_id)
        except KeyError:
            return
        palette_menu_commands = [
            item.command
            for item in menus
            if isinstance(item, MenuItem) and item.command.id not in self._exclude
        ]
        palette_menu_set = set(palette_menu_commands)
        removed = all_cmds_set - palette_menu_set
        added = palette_menu_set - all_cmds_set
        for elem in removed:
            self._list.all_commands.remove(elem)
        for elem in palette_menu_commands:
            if elem in added:
                self._list.all_commands.append(elem)
        return

    def focusOutEvent(self, a0: QtGui.QFocusEvent | None) -> None:
        """Hide the palette when focus is lost."""
        self.hide()
        return super().focusOutEvent(a0)

    def update_context(self, parent: QMainWindow) -> None:
        """Update the context of the palette."""
        self._list._app_model_context = parent._himena_main_window._ctx_keys.dict()
        return

    def show(self) -> None:
        if not self._command_initialized:
            self._initialize_commands()
        if self._need_update:
            self._update_contents()
            self._need_update = False

        self._line.setText("")
        self._list.update_for_text("")
        super().show()
        if parent := self.parentWidget():
            parent_rect = parent.rect()
            self_size = self.sizeHint()
            w = min(int(parent_rect.width() * 0.8), self_size.width())
            topleft = parent.rect().topLeft()
            topleft.setX(int(topleft.x() + (parent_rect.width() - w) / 2))
            topleft.setY(int(topleft.y() + 3))
            self.move(topleft)
            self.resize(w, self_size.height())

        self.raise_()
        self._line.setFocus()
        return

    def text(self) -> str:
        """Return the text in the line edit."""
        return self._line.text()


class QCommandLineEdit(QtW.QLineEdit):
    """The line edit used in command palette widget."""

    def commandPalette(self) -> QCommandPalette:
        """The parent command palette widget."""
        return cast(QCommandPalette, self.parent())

    def event(self, e: QtCore.QEvent | None) -> bool:
        if e is None or e.type() != QtCore.QEvent.Type.KeyPress:
            return super().event(e)
        e = cast(QtGui.QKeyEvent, e)
        if e.modifiers() in (
            Qt.KeyboardModifier.NoModifier,
            Qt.KeyboardModifier.KeypadModifier,
        ):
            key = e.key()
            if key == Qt.Key.Key_Escape:
                self.commandPalette().hide()
                return True
            if key == Qt.Key.Key_Return:
                palette = self.commandPalette()
                if palette._list.can_execute():
                    self.commandPalette().hide()
                    self.commandPalette()._list.execute()
                    return True
                return False
            if key == Qt.Key.Key_Up:
                self.commandPalette()._list.move_selection(-1)
                return True
            if key == Qt.Key.Key_PageUp:
                self.commandPalette()._list.move_selection(-10)
                return True
            if key == Qt.Key.Key_Down:
                self.commandPalette()._list.move_selection(1)
                return True
            if key == Qt.Key.Key_PageDown:
                self.commandPalette()._list.move_selection(10)
                return True
        return super().event(e)


def bold_colored(text: str, color: str) -> str:
    """Return a bolded and colored HTML text."""
    return f"<b><font color={color!r}>{text}</font></b>"


def colored(text: str, color: str) -> str:
    """Return a colored HTML text."""
    return f"<font color={color!r}>{text}</font>"


class QCommandMatchModel(QtCore.QAbstractListModel):
    """A list model for the command palette."""

    def __init__(self, parent: QtW.QWidget | None = None):
        super().__init__(parent)
        self._max_matches = 80

    def rowCount(self, parent: QtCore.QModelIndex | None = None) -> int:
        return self._max_matches

    def data(self, index: QtCore.QModelIndex, role: int = 0) -> Any:
        """Don't show any data. Texts are rendered by the item widget."""
        return QtCore.QVariant()

    def flags(self, index: QtCore.QModelIndex) -> Qt.ItemFlag:
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable


class QCommandLabel(QtW.QLabel):
    """The label widget to display a command in the palette."""

    DISABLED_COLOR = "gray"

    def __init__(self):
        super().__init__()
        self._command: CommandRule | None = None
        self._command_text: str = ""
        self._disabled = False

    def command(self) -> CommandRule | None:
        """The app-model Action bound to this label."""
        return self._command

    def set_command(self, cmd: CommandRule, as_name: str) -> None:
        """Set command to this widget."""
        self._command_text = as_name
        self._command = cmd
        self.setText(as_name.replace("\n", " "))
        self.setToolTip(cmd.tooltip)

    def command_text(self) -> str:
        """The original command text."""
        return self._command_text

    def set_text_colors(self, input_text: str, color: str) -> None:
        """Set label text color based on the input text."""
        if input_text == "":
            return
        text = self.command_text()
        words = input_text.split(" ")
        pattern = re.compile("|".join(words), re.IGNORECASE)

        output_texts: list[str] = []
        last_end = 0
        for match_obj in pattern.finditer(text):
            output_texts.append(text[last_end : match_obj.start()])
            word = match_obj.group()
            colored_word = bold_colored(word, color)
            output_texts.append(colored_word)
            last_end = match_obj.end()

        if last_end == 0 and len(input_text) < 4:  # no match word-wise
            replace_table: dict[int, str] = {}
            for char in input_text:
                idx = text.lower().find(char.lower())
                if idx >= 0:
                    replace_table[idx] = bold_colored(text[idx], color)
            for i, value in sorted(
                replace_table.items(), key=lambda x: x[0], reverse=True
            ):
                text = text[:i] + value + text[i + 1 :]
            self.setText(text)
            return

        output_texts.append(text[last_end:])
        output_text = "".join(output_texts)
        self.setText(output_text)
        return

    def disabled(self) -> bool:
        """Return true if the label is disabled."""
        return self._disabled

    def set_disabled(self, disabled: bool) -> None:
        """Set the label to disabled."""
        if disabled:
            text = self.command_text()
            self.setText(colored(text, self.DISABLED_COLOR))
        self._disabled = disabled
        return


class QCommandList(QtW.QListView):
    commandClicked = Signal(int)  # one of the items is clicked

    def __init__(
        self,
        palette: QCommandPalette,
        formatter: Callable[[Action], str],
    ) -> None:
        super().__init__()
        self._qpalette = palette
        self._commands = []
        self._formatter = formatter
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setModel(QCommandMatchModel(self))
        self.setSelectionMode(QtW.QAbstractItemView.SelectionMode.NoSelection)
        self._selected_index = 0

        # NOTE: maybe useful for fetch-and-scrolling in the future
        self._index_offset = 0

        self._label_widgets: list[QCommandLabel] = []
        self._current_max_index = 0
        for i in range(self.model()._max_matches):
            lw = QCommandLabel()
            self._label_widgets.append(lw)
            self.setIndexWidget(self.model().index(i), lw)
        self.pressed.connect(self._on_clicked)

        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._match_color = "#468cc6"
        self._app_model_context: dict[str, Any] = {}

    def _on_clicked(self, index: QtCore.QModelIndex) -> None:
        if index.isValid():
            self.commandClicked.emit(index.row())
            return

    def move_selection(self, dx: int) -> None:
        """Move selection by dx, dx can be negative or positive."""
        self._selected_index += dx
        self._selected_index = max(0, self._selected_index)
        self._selected_index = min(self._current_max_index - 1, self._selected_index)
        self.update_selection()
        return

    def update_selection(self) -> None:
        """Update the widget selection state based on the selected index."""
        index = self.model().index(self._selected_index - self._index_offset)
        if model := self.selectionModel():
            model.setCurrentIndex(
                index, QtCore.QItemSelectionModel.SelectionFlag.ClearAndSelect
            )
        return

    @property
    def all_commands(self) -> list[CommandRule]:
        return self._commands

    def extend_command(self, commands: Iterable[Action]) -> None:
        """Extend the list of commands."""
        self.all_commands.extend(commands)
        return

    def command_at(self, index: int) -> CommandRule | None:
        i = index - self._index_offset
        index_widget = self.widget_at(i)
        if index_widget is None:
            return None
        return index_widget.command()

    def iter_widgets(self) -> Iterator[QCommandLabel]:
        """Iterate over all the index widgets."""
        yield from self._label_widgets

    def iter_command(self) -> Iterator[CommandRule]:
        """Iterate over all the commands registered to this command list widget."""
        for i in range(self.model().rowCount()):
            if not self.isRowHidden(i):
                command = self.command_at(i)
                if command is not None:
                    yield command

    def execute(self, index: int | None = None) -> None:
        """Execute the currently selected command."""
        if index is None:
            index = self._selected_index
        command = self.command_at(index)
        if command is None:
            return
        self._exec_action(command)
        # move to the top
        self.all_commands.remove(command)
        self.all_commands.insert(0, command)
        return

    def _exec_action(self, action: CommandRule):
        app = self._qpalette._model_app
        return app.commands.execute_command(action.id).result()

    def can_execute(self) -> bool:
        """Return true if the command can be executed."""
        index = self._selected_index
        command = self.command_at(index)
        if command is None:
            return False
        return _enabled(command, self._app_model_context)

    def widget_at(self, index: int) -> QCommandLabel | None:
        i = index - self._index_offset
        return self.indexWidget(self.model().index(i))

    def update_for_text(self, input_text: str) -> None:
        """Update the list to match the input text."""
        self._selected_index = 0
        max_matches = self.model()._max_matches
        row = 0
        for row, action in enumerate(self.iter_top_hits(input_text)):
            self.setRowHidden(row, False)
            lw = self.widget_at(row)
            if lw is None:
                self._current_max_index = row
                break
            lw.set_command(action, self._formatter(action))
            if _enabled(action, self._app_model_context):
                lw.set_disabled(False)
                lw.set_text_colors(input_text, color=self._match_color)
            else:
                lw.set_disabled(True)

            if row >= max_matches:
                self._current_max_index = max_matches
                break
            row = row + 1
        else:
            # if the loop completes without break
            self._current_max_index = row
            for r in range(row, max_matches):
                self.setRowHidden(r, True)
        self.update_selection()
        return

    def iter_top_hits(self, input_text: str) -> Iterator[CommandRule]:
        """Iterate over the top hits for the input text"""
        commands: list[tuple[float, CommandRule]] = []
        for command in self.all_commands:
            score = _match_score(self._formatter(command), input_text)
            if score > 0.0:
                if _enabled(command, self._app_model_context):
                    score += 10.0
                commands.append((score, command))
        commands.sort(key=lambda x: x[0], reverse=True)
        for _, command in commands:
            yield command

    if TYPE_CHECKING:

        def model(self) -> QCommandMatchModel: ...
        def indexWidget(self, index: QtCore.QModelIndex) -> QCommandLabel | None: ...


def _enabled(action: CommandRule, context: Mapping[str, Any]) -> bool:
    if action.enablement is None:
        return True
    try:
        return action.enablement.eval(context)
    except NameError:
        return False


def _match_score(command_text: str, input_text: str) -> float:
    """Return a match score (between 0 and 1) for the input text."""
    name = command_text.lower()
    if all(word in name for word in input_text.lower().split(" ")):
        return 1.0
    if len(input_text) < 4 and all(char in name for char in input_text.lower()):
        return 0.7
    return 0.0
