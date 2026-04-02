from __future__ import annotations

import re
import logging
from collections.abc import Iterator, Mapping
from typing import TYPE_CHECKING, Any, Iterable, cast, Callable

from app_model import Application
from app_model.types import CommandRule, MenuItem, Action
from himena._app_model.utils import collect_commands
from qtpy import QtCore, QtGui, QtWidgets as QtW
from qtpy.QtCore import Qt, Signal

if TYPE_CHECKING:
    from himena.qt.main_window import QMainWindow

_LOGGER = logging.getLogger(__name__)


class QCommandPaletteBase(QtW.QFrame):
    palette_hidden = Signal()  # emitted when the palette is hidden

    def __init__(
        self,
        parent: QtW.QWidget | None = None,
        formatter: Callable[[Action], str] = lambda x: x.title,
        placeholder: str = "Search commands by name ...",
    ):
        super().__init__(parent)
        self._need_initialize = True
        self._need_update = False  # needs update before showing the palette

        # Add shadow effect
        shadow = QtW.QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setXOffset(0)
        shadow.setYOffset(5)
        shadow.setColor(QtGui.QColor(0, 0, 0, 100))
        self.setGraphicsEffect(shadow)

        self._line = QCommandLineEdit()
        self._line.setPlaceholderText(placeholder)
        self._list = QCommandList(formatter)
        _layout = QtW.QVBoxLayout(self)
        _layout.addWidget(self._line)
        _layout.addWidget(self._list)
        self._layout = _layout

        font = self.font()
        font.setPointSize(14)
        self.setFont(font)
        self._line.setFont(font)
        font = self._list.font()
        font.setPointSize(11)
        self._list.setFont(font)
        self.hide()

        self._line.textChanged.connect(self._on_text_changed)
        self._line.editingFinished.connect(self.hide)
        self._list.exec_requested.connect(self._on_command_exec_requested)

    def _initialize_commands(self) -> None:
        """Initialize the command list. Should be called before showing the palette."""

    def _update_contents(self) -> None:
        """Update the command list based on the current app model."""

    def _on_command_exec_requested(self, cmd: CommandRule) -> None:
        """Handle the request to execute a command."""
        raise NotImplementedError

    def sizeHint(self) -> QtCore.QSize:
        return QtCore.QSize(600, 400)

    def extend_command(self, list_of_commands: Iterable[CommandRule]) -> None:
        self._list.extend_command(list_of_commands)

    def _on_text_changed(self, text: str) -> None:
        self._list.update_for_text(text)

    def focusOutEvent(self, a0: QtGui.QFocusEvent | None) -> None:
        """Hide the palette when focus is lost."""
        self.hide()
        return super().focusOutEvent(a0)

    def hide(self) -> None:
        super().hide()
        self.palette_hidden.emit()

    def update_context(self, parent: QMainWindow) -> None:
        """Update the context of the palette."""
        self._list._app_model_context = parent._himena_main_window._ctx_keys.dict()

    def show(self) -> None:
        if self._need_initialize:
            self._initialize_commands()
            self._need_initialize = False
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


class QCommandPaletteDialog(QCommandPaletteBase):
    def __init__(self, parent: QtW.QWidget | None = None):
        super().__init__(parent, placeholder="Choose one ...")
        self._title_label = QtW.QLabel()
        self._layout.insertWidget(0, self._title_label)
        self._response: Any | None = None
        self._choice_map: dict[str, Any] = {}

    def set_title_message(self, title: str, message: str) -> None:
        if title.strip():
            self._title_label.setText(f"<b>{title}</b>")
            self._title_label.show()
        else:
            self._title_label.hide()
        self._line.setPlaceholderText(message)

    def set_choices(self, choices: list[tuple[str, Any]]):
        self._choice_map = dict(choices)
        commands = [CommandRule(id=txt, title=txt) for txt in self._choice_map.keys()]
        self.extend_command(commands)

    def _on_command_exec_requested(self, cmd: CommandRule) -> None:
        self._response = self._choice_map.get(cmd.id)
        self.hide()

    def exec(self) -> Any | None:
        """Show the palette and return the chosen response."""
        self._response = None
        self.show()
        loop = QtCore.QEventLoop()
        self.palette_hidden.connect(loop.quit)
        loop.exec()
        return self._response


class QCommandPalette(QCommandPaletteBase):
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
        super().__init__(parent, formatter, placeholder)

        self._menu_id = menu_id or app.menus.COMMAND_PALETTE_ID
        self._exclude = set(exclude)

        app.menus.menus_changed.connect(self._on_app_menus_changed)
        self._model_app = app

    def _initialize_commands(self) -> None:
        app = self._model_app
        try:
            menu_items = app.menus.get_menu(self._menu_id)
            commands = collect_commands(app, menu_items, self._exclude)
            self.extend_command(commands)
        except KeyError:
            pass
        _LOGGER.info("Command palette initialized.")

    def _on_command_exec_requested(self, cmd: CommandRule) -> None:
        app = self._model_app
        app.commands.execute_command(cmd.id).result()
        self.hide()

    def _on_app_menus_changed(self, changed_menus: set[str]) -> None:
        """Connected to app_model.menus.menus_changed."""
        if self._menu_id not in changed_menus:
            return
        self._need_update = True

    def _update_contents(self) -> None:
        """Update widget based on the current state of the app model."""
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


class QCommandLineEdit(QtW.QLineEdit):
    """The line edit used in command palette widget."""

    def commandPalette(self) -> QCommandPaletteBase:
        """The parent command palette widget."""
        return cast(QCommandPaletteBase, self.parent())

    def event(self, e: QtCore.QEvent | None) -> bool:
        if e is None or e.type() != QtCore.QEvent.Type.KeyPress:
            return super().event(e)
        e = cast(QtGui.QKeyEvent, e)
        if e.modifiers() in (
            Qt.KeyboardModifier.NoModifier,
            Qt.KeyboardModifier.KeypadModifier,
        ):
            palette = self.commandPalette()
            list_widget = palette._list
            match e.key():
                case Qt.Key.Key_Escape:
                    palette.hide()
                    return True
                case Qt.Key.Key_Return:
                    if list_widget.can_execute():
                        list_widget.execute()
                        return True
                    return False
                case Qt.Key.Key_Up:
                    list_widget.move_selection(-1)
                    return True
                case Qt.Key.Key_PageUp:
                    list_widget.move_selection(-10)
                    return True
                case Qt.Key.Key_Down:
                    list_widget.move_selection(1)
                    return True
                case Qt.Key.Key_PageDown:
                    list_widget.move_selection(10)
                    return True
        return super().event(e)


def bold_colored(text: str, color: str) -> str:
    """Return a bolded and colored HTML text."""
    return f"<b><font color={color!r}>{text}</font></b>"


def colored(text: str, color: str) -> str:
    """Return a colored HTML text."""
    return f"<font color={color!r}>{text}</font>"


_QCOMMAND_PALETTE_FLAGS = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable


class QCommandMatchModel(QtCore.QAbstractListModel):
    """A list model for the command palette."""

    def __init__(self, parent: QtW.QWidget | None = None):
        super().__init__(parent)
        self._max_matches = 80

    def rowCount(self, parent: QtCore.QModelIndex = None) -> int:
        return self._max_matches

    def data(self, index: QtCore.QModelIndex, role: int = 0) -> Any:
        """Don't show any data. Texts are rendered by the item widget."""
        if role == Qt.ItemDataRole.SizeHintRole:
            return QtCore.QSize(200, 24)
        return None

    def flags(self, index: QtCore.QModelIndex) -> Qt.ItemFlag:
        return _QCOMMAND_PALETTE_FLAGS


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
        self.setText(output_text.replace("\n", " "))
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


class QCommandList(QtW.QListView):
    exec_requested = Signal(CommandRule)  # request to execute the command

    def __init__(self, formatter: Callable[[Action], str]):
        super().__init__()
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
            row = index.row()
            index_widget = self.widget_at(row)
            if index_widget is None or index_widget.disabled():
                return
            self.execute(row)

    def move_selection(self, dx: int) -> None:
        """Move selection by dx, dx can be negative or positive."""
        self._selected_index += dx
        self._selected_index = max(0, self._selected_index)
        self._selected_index = min(self._current_max_index - 1, self._selected_index)
        self.update_selection()

    def update_selection(self) -> None:
        """Update the widget selection state based on the selected index."""
        index = self.model().index(self._selected_index - self._index_offset)
        if model := self.selectionModel():
            model.setCurrentIndex(
                index, QtCore.QItemSelectionModel.SelectionFlag.ClearAndSelect
            )

    @property
    def all_commands(self) -> list[CommandRule]:
        return self._commands

    def extend_command(self, commands: Iterable[Action]) -> None:
        """Extend the list of commands."""
        self.all_commands.extend(commands)

    def command_at(self, index: int) -> CommandRule | None:
        if index_widget := self.widget_at(index - self._index_offset):
            return index_widget.command()

    def execute(self, index: int | None = None) -> None:
        """Execute the currently selected command."""
        if self._current_max_index == 0:
            return
        if index is None:
            index = self._selected_index
        if (command := self.command_at(index)) is not None:
            self.exec_requested.emit(command)
            # move to the top
            self.all_commands.remove(command)
            self.all_commands.insert(0, command)

    def can_execute(self) -> bool:
        """Return true if the command can be executed."""
        index = self._selected_index
        command = self.command_at(index)
        if command is None:
            return False
        return _enabled(command, self._app_model_context)

    def widget_at(self, index: int) -> QCommandLabel | None:
        """Return the label widget at the given index."""
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
