from __future__ import annotations

from enum import Enum, auto
from io import StringIO
from typing import TYPE_CHECKING, Any, Iterable, Literal, Mapping
from dataclasses import dataclass
import numpy as np

from qtpy import QtWidgets as QtW
from qtpy import QtGui, QtCore
from qtpy.QtCore import Qt

from himena.consts import StandardType
from himena.types import WidgetDataModel
from himena.standards.model_meta import TableMeta
from himena.plugins import protocol_override
from himena_builtins.qt.widgets._table_components import QTableBase, QSelectionRangeEdit
from himena._utils import UndoRedoStack


class HeaderFormat(Enum):
    """Enum of how to index table header."""

    NumberZeroIndexed = auto()
    NumberOneIndexed = auto()
    Alphabetic = auto()


@dataclass
class TableAction:
    """Base class for table undo/redo actions."""

    def invert(self) -> TableAction:
        return self

    def apply(self, table: QSpreadsheet):
        raise NotImplementedError("Apply method must be implemented.")


@dataclass
class EditAction(TableAction):
    old: str | np.ndarray
    new: str | np.ndarray
    index: tuple[int | slice, int | slice]

    def invert(self) -> TableAction:
        return EditAction(self.new, self.old, self.index)

    def apply(self, table: QSpreadsheet):
        return table.array_update(self.index, self.new, record_undo=False)


@dataclass
class ReshapeAction(TableAction):
    old: tuple[int, int]
    new: tuple[int, int]

    def invert(self) -> TableAction:
        return ReshapeAction(self.new, self.old)

    def apply(self, table: QSpreadsheet):
        r_old, c_old = self.old
        r_new, c_new = self.new
        if r_old == r_new and c_old == c_new:
            pass
        elif r_old < r_new and c_old < c_new:
            table.array_expand(r_new - r_old, c_new - c_old)
        elif r_old > r_new and c_old > c_new:
            table.array_shrink(r_new, r_new)
        else:
            raise ValueError(
                f"This reshape ({self.old} -> {self.new}) is not supported."
            )


@dataclass
class InsertAction(TableAction):
    index: int
    axis: Literal[0, 1]
    array: np.ndarray | None = None

    def invert(self) -> TableAction:
        return RemoveAction(self.index, self.axis, self.array)

    def apply(self, table: QSpreadsheet):
        table.array_insert(self.index, self.axis, self.array, record_undo=False)


@dataclass
class RemoveAction(TableAction):
    index: int
    axis: Literal[0, 1]
    array: np.ndarray

    def invert(self) -> TableAction:
        return InsertAction(self.index, self.axis, self.array)

    def apply(self, table: QSpreadsheet):
        table.array_delete([self.index], self.axis, record_undo=False)


@dataclass
class ActionGroup(TableAction):
    actions: list[TableAction]  # operation from actions[0] to actions[-1]

    def invert(self) -> TableAction:
        return ActionGroup([action.invert() for action in self.actions[::-1]])

    def apply(self, table: QSpreadsheet):
        for action in self.actions:
            action.apply(table)


_FLAGS = (
    Qt.ItemFlag.ItemIsEnabled
    | Qt.ItemFlag.ItemIsSelectable
    | Qt.ItemFlag.ItemIsEditable
)


class QStringArrayModel(QtCore.QAbstractTableModel):
    """Table model for a string array."""

    def __init__(self, arr: np.ndarray, parent: QSpreadsheet):
        super().__init__(parent)
        self._arr = arr  # 2D
        if arr.ndim != 2:
            raise ValueError("Only 2D array is supported.")
        if not isinstance(arr.dtype, np.dtypes.StringDType):
            raise ValueError("Only string array is supported.")
        self._nrows, self._ncols = arr.shape
        self._header_format = HeaderFormat.NumberZeroIndexed

    if TYPE_CHECKING:

        def parent(self) -> QSpreadsheet: ...  # fmt: skip

    def rowCount(self, parent=None):
        return max(self._nrows + 1, 100)

    def columnCount(self, parent=None):
        return max(self._ncols + 1, 30)

    def flags(self, index: QtCore.QModelIndex) -> Qt.ItemFlags:
        return _FLAGS

    def data(
        self,
        index: QtCore.QModelIndex,
        role: Qt.ItemDataRole = Qt.ItemDataRole.DisplayRole,
    ):
        if not index.isValid():
            return QtCore.QVariant()
        r, c = index.row(), index.column()
        if r >= self._arr.shape[0] or c >= self._arr.shape[1]:
            return QtCore.QVariant()
        if role == Qt.ItemDataRole.TextAlignmentRole:
            return Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        if role == Qt.ItemDataRole.ToolTipRole:
            return f"A[{r}, {c}] = {self._arr[r, c]}"
        if role in [Qt.ItemDataRole.EditRole, Qt.ItemDataRole.DisplayRole]:
            return str(self._arr[r, c])
        return QtCore.QVariant()

    def setData(self, index: QtCore.QModelIndex, value: Any, role: int = ...) -> bool:
        if role == Qt.ItemDataRole.EditRole:
            qtable = self.parent()
            qtable.array_update((index.row(), index.column()), value, record_undo=True)
            return True
        return False

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ):
        if role != Qt.ItemDataRole.DisplayRole:
            return QtCore.QVariant()
        if self._header_format is HeaderFormat.NumberZeroIndexed:
            return str(section)
        elif self._header_format is HeaderFormat.NumberOneIndexed:
            return str(section + 1)
        elif self._header_format is HeaderFormat.Alphabetic:
            if orientation == Qt.Orientation.Horizontal:
                return str(char_arange(section, section + 1)[0])
            else:
                return str(section + 1)


_EDITABLE = (
    QtW.QAbstractItemView.EditTrigger.DoubleClicked
    | QtW.QAbstractItemView.EditTrigger.EditKeyPressed
)
_NOT_EDITABLE = QtW.QAbstractItemView.EditTrigger.NoEditTriggers


class QSpreadsheet(QTableBase):
    """Table widget for editing a 2D string array."""

    __himena_widget_id__ = "builtins:QSpreadsheet"
    __himena_display_name__ = "Built-in Spreadsheet Editor"
    HeaderFormat = HeaderFormat

    def __init__(self):
        QTableBase.__init__(self)
        self.setEditTriggers(_EDITABLE)
        self._control = None
        self._model_type = StandardType.TABLE
        self._undo_stack = UndoRedoStack[TableAction](size=25)
        self._modified_override: bool | None = None

    def setHeaderFormat(self, value: HeaderFormat) -> None:
        if model := self.model():
            model._header_format = value

    def data_shape(self) -> tuple[int, int]:
        return self.model()._arr.shape

    @protocol_override
    def update_model(self, model: WidgetDataModel) -> None:
        value = model.value
        if value is None:
            table = np.empty((0, 0), dtype=np.dtypes.StringDType())
        else:
            if isinstance(value, Mapping):
                table = _dict_to_array(value)
            else:
                table = _array_like_to_array(value)
            if table.ndim < 2:
                table = table.reshape(-1, 1)
        if self.model() is None:
            self.setModel(QStringArrayModel(table, self))
        else:
            self.model()._arr = table
        sep: str | None = None
        if isinstance(meta := model.metadata, TableMeta):
            if meta.separator is not None:
                sep = meta.separator
            if (pos := meta.current_position) is not None:
                index = self.model().index(*pos)
                self.setCurrentIndex(index)
                self._selection_model.current_index = pos
            if meta.selections:  # if has selections, they need updating
                self._selection_model.clear()
            for (r0, r1), (c0, c1) in meta.selections:
                self._selection_model.append((slice(r0, r1), slice(c0, c1)))

        self._undo_stack.clear()
        self._modified_override = None
        self.update()

        # update control widget
        if self._control is None:
            self._control = QTableControl(self)
        self._control.update_for_table(self)
        if sep is not None:
            self._control._separator_label.setText(f"Sep: {sep!r}")
            self._control._separator = sep
            self._control._separator_label.show()
        else:
            self._control._separator = None
            self._control._separator_label.hide()
        self._model_type = model.type
        return None

    @protocol_override
    def to_model(self) -> WidgetDataModel[np.ndarray]:
        meta = self._prep_table_meta()
        if sep := self._control._separator:
            meta.separator = sep
        return WidgetDataModel(
            value=self.model()._arr,
            type=self.model_type(),
            extension_default=".csv",
            metadata=meta,
        )

    @protocol_override
    def model_type(self):
        return self._model_type

    @protocol_override
    def is_modified(self) -> bool:
        if self._modified_override is not None:
            return self._modified_override
        return self._undo_stack.undoable()

    @protocol_override
    def set_modified(self, value: bool) -> None:
        self._modified_override = value

    @protocol_override
    def set_editable(self, value: bool) -> None:
        if value:
            trig = _EDITABLE
        else:
            trig = _NOT_EDITABLE
        self.setEditTriggers(trig)

    @protocol_override
    def control_widget(self) -> QTableControl:
        return self._control

    def array_update(
        self,
        index: tuple[int, int],
        value: str,
        *,
        record_undo: bool = True,
    ) -> None:
        """Update the data at the given index."""
        r, c = index
        arr = self.model()._arr
        _ud_old_shape = arr.shape
        if r >= arr.shape[0] or c >= arr.shape[1]:  # need expansion
            _ud_old_data = ""
            _ud_old_shape = arr.shape
            self.array_expand(r + 1, c + 1)
            _ud_new_shape = arr.shape
            _action_reshape = ReshapeAction(_ud_old_shape, _ud_new_shape)
            arr = self.model()._arr
        else:
            _ud_old_data = arr[r, c]
            _action_reshape = None
        arr[r, c] = str(value)
        _ud_new_data = arr[r, c]
        _action = EditAction(_ud_old_data, _ud_new_data, (r, c))
        if _action_reshape is not None:
            _action = ActionGroup([_action_reshape, _action])
        if record_undo:
            self._undo_stack.push(_action)

    def array_expand(self, nr: int, nc: int):
        """Expand the array to the given shape."""
        nr0, nc0 = self.model()._arr.shape
        self.model()._arr = np.pad(
            self.model()._arr,
            [(0, max(nr - nr0, 0)), (0, max(nc - nc0, 0))],
            mode="constant",
            constant_values="",
        )

    def array_shrink(self, nr: int, nc: int):
        """Shrink the array to the given shape."""
        self.model()._arr = self.model()._arr[:nr, :nc]

    def array_insert(
        self,
        index: int,
        axis: Literal[0, 1],
        values: np.ndarray | None = None,
        *,
        record_undo: bool = True,
    ) -> None:
        """Insert an empty array at the given index."""
        arr = self.model()._arr
        if values is None:
            self.model()._arr = np.insert(arr, index, "", axis=axis)
        else:
            self.model()._arr = np.insert(arr, index, values, axis=axis)
        if record_undo:
            self._undo_stack.push(InsertAction(index, axis, values))
        self.update()

    def array_delete(
        self,
        indices: int | Iterable[int],
        axis: Literal[0, 1],
        *,
        record_undo: bool = True,
    ):
        """Remove the array at the given index."""
        _action = ActionGroup(
            [
                RemoveAction(idx, axis, self.model()._arr[idx].copy())
                for idx in sorted(indices, reverse=True)
            ]
        )
        self.model()._arr = np.delete(self.model()._arr, list(indices), axis=axis)
        self.update()
        if record_undo:
            self._undo_stack.push(_action)

    def undo(self):
        if action := self._undo_stack.undo():
            action.invert().apply(self)
            self.update()

    def redo(self):
        if action := self._undo_stack.redo():
            action.apply(self)
            self.update()

    def _copy_to_clipboard(self):
        sels = self._selection_model.ranges
        if len(sels) != 1:
            return
        sel = sels[0]
        values = self.model()._arr[sel]
        if values.size > 0:
            string = "\n".join(["\t".join(cells) for cells in values])
            QtW.QApplication.clipboard().setText(string)

    def _paste_from_clipboard(self):
        idx = self._selection_model.current_index
        text = QtW.QApplication.clipboard().text()
        if not text:
            return

        buf = StringIO(text)
        arr_paste = np.loadtxt(
            buf, dtype=np.dtypes.StringDType(), delimiter="\t", ndmin=2
        )
        # undo info
        arr = self.model()._arr
        row0, col0 = idx.row, idx.column
        lr, lc = arr_paste.shape
        sl = (slice(row0, row0 + lr), slice(col0, col0 + lc))
        _ud_old_shape = self.data_shape()
        _ud_old_data = arr[sl].copy()

        self._paste_array((idx.row, idx.column), arr_paste)

        # undo info
        _ud_new_shape = self.data_shape()
        _ud_new_data = arr_paste.copy()
        _action_edit = EditAction(_ud_old_data, _ud_new_data, sl)
        if _ud_old_shape == _ud_new_shape:
            _action = _action_edit
        else:
            _action_reshape = ReshapeAction(_ud_old_shape, _ud_new_shape)
            _action = ActionGroup([_action_reshape, _action_edit])
        self._undo_stack.push(_action)

    def _paste_array(self, origin: tuple[int, int], arr_paste: np.ndarray):
        arr = self.model()._arr
        # paste in the text
        row0, col0 = origin
        lr, lc = arr_paste.shape

        # expand the table if necessary
        if (row0 + lr) > arr.shape[0]:
            arr = np.pad(
                arr,
                [(0, row0 + lr - arr.shape[0]), (0, 0)],
                mode="constant",
                constant_values="",
            )
        if (col0 + lc) > arr.shape[1]:
            arr = np.pad(
                arr,
                [(0, 0), (0, col0 + lc - arr.shape[1])],
                mode="constant",
                constant_values="",
            )

        # paste the data
        arr[row0 : row0 + lr, col0 : col0 + lc] = arr_paste
        self.model()._arr = arr

        # select what was just pasted
        self._selection_model.set_ranges(
            [(slice(row0, row0 + lr), slice(col0, col0 + lc))]
        )
        self.update()

    def _delete_selection(self):
        _actions = []
        for sel in self._selection_model.ranges:
            old_array = self.model()._arr.copy()
            new_array = np.zeros_like(old_array)
            _actions.append(EditAction(old_array, new_array, sel))
            self.model()._arr[sel] = ""
        self.update()
        self._undo_stack.push(ActionGroup(_actions))

    def _insert_row_below(self):
        self.array_insert(self._selection_model.current_index.row + 1, 0)

    def _insert_row_above(self):
        self.array_insert(self._selection_model.current_index.row, 0)

    def _insert_column_right(self):
        self.array_insert(self._selection_model.current_index.column + 1, 1)

    def _insert_column_left(self):
        self.array_insert(self._selection_model.current_index.column, 1)

    def _remove_selected_rows(self):
        selected_rows = set[int]()
        for sel in self._selection_model.ranges:
            selected_rows.update(range(sel[0].start, sel[0].stop))
        self.array_delete(selected_rows, 0)

    def _remove_selected_columns(self):
        selected_cols = set[int]()
        for sel in self._selection_model.ranges:
            selected_cols.update(range(sel[1].start, sel[1].stop))
        self.array_delete(selected_cols, 1)

    def keyPressEvent(self, e: QtGui.QKeyEvent):
        _Ctrl = QtCore.Qt.KeyboardModifier.ControlModifier
        if e.modifiers() & _Ctrl and e.key() == QtCore.Qt.Key.Key_C:
            return self._copy_to_clipboard()
        elif e.modifiers() & _Ctrl and e.key() == QtCore.Qt.Key.Key_V:
            return self._paste_from_clipboard()
        elif e.modifiers() & _Ctrl and e.key() == QtCore.Qt.Key.Key_X:
            self._copy_to_clipboard()
            return self._delete_selection()
        elif e.key() in (QtCore.Qt.Key.Key_Delete, QtCore.Qt.Key.Key_Backspace):
            return self._delete_selection()
        elif e.modifiers() & _Ctrl and e.key() == QtCore.Qt.Key.Key_F:
            self._find_string()
            return
        elif e.modifiers() & _Ctrl and e.key() == QtCore.Qt.Key.Key_Z:
            self.undo()
            return
        elif e.modifiers() & _Ctrl and e.key() == QtCore.Qt.Key.Key_Y:
            self.redo()
            return
        elif (
            (not (e.modifiers() & _Ctrl))
            and (
                e.modifiers() == QtCore.Qt.KeyboardModifier.NoModifier
                or e.modifiers() & QtCore.Qt.KeyboardModifier.ShiftModifier
            )
            and Qt.Key.Key_Space <= e.key() <= Qt.Key.Key_ydiaeresis
        ):
            index = self._selection_model.current_index
            qindex = self.model().index(index.row, index.column)
            self.edit(qindex)
            if editor := self.itemDelegate()._current_editor:
                editor.setText(e.text())
            return
        return super().keyPressEvent(e)

    if TYPE_CHECKING:

        def model(self) -> QStringArrayModel: ...


_R_CENTER = QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter


class QTableControl(QtW.QWidget):
    def __init__(self, table: QTableBase):
        super().__init__()
        layout = QtW.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(_R_CENTER)
        self._label = QtW.QLabel("")
        self._label.setAlignment(_R_CENTER)

        # toolbuttons
        self._insert_menu_button = QtW.QPushButton()
        self._insert_menu_button.setText("Ins")  # or "icons8:plus"
        self._insert_menu_button.setMenu(self._make_insert_menu(table))
        self._remove_menu_button = QtW.QPushButton()
        self._remove_menu_button.setText("Rem")
        self._remove_menu_button.setMenu(self._make_delete_menu(table))

        self._separator_label = QtW.QLabel()
        self._separator: str | None = None

        empty = QtW.QWidget()
        empty.setSizePolicy(
            QtW.QSizePolicy.Policy.Expanding, QtW.QSizePolicy.Policy.Preferred
        )
        layout.addWidget(empty)  # empty space
        layout.addWidget(self._label)
        layout.addWidget(self._insert_menu_button)
        layout.addWidget(self._remove_menu_button)
        layout.addWidget(self._separator_label)
        layout.addWidget(QSelectionRangeEdit(table))

    def update_for_table(self, table: QSpreadsheet):
        shape = table.model()._arr.shape
        self._label.setText(f"Shape {shape!r}")
        return None

    def _make_insert_menu(self, table: QSpreadsheet):
        menu = QtW.QMenu(self)
        menu.addAction("Row above", table._insert_row_above)
        menu.addAction("Row below", table._insert_row_below)
        menu.addAction("Column left", table._insert_column_left)
        menu.addAction("Column right", table._insert_column_right)
        return menu

    def _make_delete_menu(self, table: QSpreadsheet):
        menu = QtW.QMenu(self)
        menu.addAction("Rows", table._remove_selected_rows)
        menu.addAction("Columns", table._remove_selected_columns)
        return menu


ORD_A = ord("A")
CHARS = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ") + [""]
LONGEST = CHARS[:-1]


def _iter_char(start: int, stop: int):
    if stop >= 26**4:
        raise ValueError("Stop must be less than 26**4 - 1")
    base_repr = np.base_repr(start, 26)
    current = np.zeros(4, dtype=np.int8)
    offset = 4 - len(base_repr)
    for i, d in enumerate(base_repr):
        current[i + offset] = int(d, 26)

    current[:3] -= 1
    for _ in range(start, stop):
        yield "".join(CHARS[s] for s in current)
        current[3] += 1
        for i in [3, 2, 1]:
            if current[i] >= 26:
                over = current[i] - 25
                current[i] = 0
                current[i - 1] += over


def char_arange(start: int, stop: int | None = None):
    """
    A char version of np.arange.

    Examples
    --------
    >>> char_arange(3)  # array(["A", "B", "C"])
    >>> char_arange(25, 28)  # array(["Z", "AA", "AB"])
    """
    global LONGEST
    if stop is None:
        start, stop = 0, start
    nmax = len(LONGEST)
    if stop <= nmax:
        return np.array(LONGEST[start:stop], dtype="<U4")
    LONGEST = np.append(LONGEST, np.fromiter(_iter_char(nmax, stop), dtype="<U4"))
    return LONGEST[start:].copy()


def _dict_to_array(value: dict[str, str]) -> np.ndarray:
    keys = list(value.keys())
    values = list(value.values())
    max_column_length = max(len(k) for k in values)
    arr = np.zeros((max_column_length + 1, len(keys)), dtype=np.dtypes.StringDType())
    arr[0, :] = keys
    for i, column in enumerate(values):
        arr[1:, i] = column
    return arr


def _array_like_to_array(value) -> np.ndarray:
    table = np.asarray(value, dtype=np.dtypes.StringDType())
    if table.ndim < 2:
        table = table.reshape(-1, 1)
    return table