from __future__ import annotations

from enum import Enum, auto
from io import StringIO
from pathlib import Path
from typing import TYPE_CHECKING, Any, Iterable, Literal, Mapping
from dataclasses import dataclass
import numpy as np
from numpy.typing import NDArray

from qtpy import QtWidgets as QtW
from qtpy import QtGui, QtCore
from qtpy.QtCore import Qt

from himena.consts import StandardType
from himena.qt._utils import get_main_window
from himena.style import Theme
from himena.types import WidgetDataModel
from himena.standards.model_meta import TableMeta
from himena.qt._qsvg import QColoredSVGIcon
from himena.plugins import validate_protocol, config_field
from himena_builtins.qt.widgets._table_components import (
    QTableBase,
    QSelectionRangeEdit,
    FLAGS,
    Editability,
)
from himena.utils.collections import UndoRedoStack
from himena.utils.misc import table_to_text


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
            table.array_expand(r_new, c_new)
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


class QStringArrayModel(QtCore.QAbstractTableModel):
    """Table model for a string array."""

    MIN_ROW_COUNT = 100
    MIN_COLUMN_COUNT = 30

    def __init__(self, arr: np.ndarray, parent: QSpreadsheet):
        super().__init__(parent)
        self._arr = arr  # 2D
        if arr.ndim != 2:
            raise ValueError("Only 2D array is supported.")
        if not isinstance(arr.dtype, np.dtypes.StringDType):
            raise ValueError("Only string array is supported.")
        self._nrows, self._ncols = arr.shape
        self._is_original_array = True
        self._header_format = HeaderFormat.NumberZeroIndexed

    @classmethod
    def empty(cls, parent: QSpreadsheet) -> QStringArrayModel:
        return cls(np.empty((0, 0), dtype=np.dtypes.StringDType()), parent)

    if TYPE_CHECKING:

        def parent(self) -> QSpreadsheet: ...  # fmt: skip

    def rowCount(self, parent=None):
        return max(self._nrows + 1, self.MIN_ROW_COUNT)

    def columnCount(self, parent=None):
        return max(self._ncols + 1, self.MIN_COLUMN_COUNT)

    def set_array(self, arr: np.ndarray, is_original: bool = True) -> None:
        if arr.ndim != 2:
            raise ValueError("Only 2D array is supported.")
        nr, nc = arr.shape
        nr0, nc0 = self.rowCount(), self.columnCount()
        self._arr = arr
        self._nrows, self._ncols = arr.shape

        # adjust the model size to fit the new array.
        _index = QtCore.QModelIndex()
        if nr + 1 > nr0:
            self.beginInsertRows(_index, nr0, nr)
            self.insertRows(nr0, nr + 1 - nr0, _index)
            self.endInsertRows()
        elif nr + 1 < nr0:
            nr_next = max(self.MIN_ROW_COUNT, nr + 1)
            self.beginRemoveRows(_index, nr_next, nr0 - 1)
            self.removeRows(nr_next, nr0 - nr_next - 2, _index)
            self.endRemoveRows()
        if nc + 1 > nc0:
            self.beginInsertColumns(_index, nc0, nc)
            self.insertColumns(nc0, nc + 1 - nc0, _index)
            self.endInsertColumns()
        elif nc + 1 < nc0:
            nc_next = max(self.MIN_COLUMN_COUNT, nc + 1)
            self.beginRemoveColumns(_index, nc_next, nc0 - 1)
            self.removeColumns(nc_next, nc0 - nc_next - 2, _index)
            self.endRemoveColumns()
        if not (is_original and self._is_original_array):
            # no need for further copy-on-write
            self._is_original_array = False

    def flags(self, index: QtCore.QModelIndex) -> Qt.ItemFlag:
        return FLAGS

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


SEP_NAMES = {"\t": "Tab", " ": "Space", ",": "Comma", ";": "Semicolon"}


class QSpreadsheet(QTableBase):
    """Table widget for editing a 2D string array.

    ## Basic Usage

    Moving, selecting, editing and copying/pasting cells are supported like many other
    spreadsheet applications.

    ## Keyboard Shortcuts

    - `↑`, `↓`, `←`, `→`: Move the current cell.
    - `PgUp`, `PgDn`, `Home`, `End`: Move the current cell by 10.
    - `Ctrl+↑`, `Ctrl+↓`, `Ctrl+←`, `Ctrl+→`: Move the current cell to the edge.
    - `Shift` with the above keys: Extend the selection.
    - `Ctrl+X`: Cut the selected cells.
    - `Ctrl+C`: Copy the selected cells to the clipboard.
    - `Ctrl+V`: Paste the clipboard content to the selected cells.
    - `Ctrl+Z`: Undo the last action.
    - `Ctrl+Y`: Redo the last undone action.
    - `Ctrl+A`: Select all cells.
    - `F2`: Start editing the current cell.
    - `Ctrl+F`: Find a string in the table.

    ## Mouse Interaction

    - Click on a cell to select it.
    - Drag to select multiple cells.
    - Double click on a cell to edit it.
    - Right click for a context menu.
    - Right drag to scroll the table.
    """

    __himena_widget_id__ = "builtins:QSpreadsheet"
    __himena_display_name__ = "Built-in Spreadsheet Editor"
    HeaderFormat = HeaderFormat

    def __init__(self):
        QTableBase.__init__(self)
        self.setEditTriggers(Editability.TRUE)
        self._control = None
        self._model_type = StandardType.TABLE
        self._undo_stack = UndoRedoStack[TableAction](size=25)
        self._sep_on_copy = "\t"
        self._extension_default = ".csv"
        self.setModel(QStringArrayModel.empty(self))

    def setHeaderFormat(self, value: HeaderFormat) -> None:
        if model := self.model():
            model._header_format = value

    def data_shape(self) -> tuple[int, int]:
        return self.model()._arr.shape

    @validate_protocol
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
            self.model().set_array(table)
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
            self._control._separator_label.setText(f"Sep: {SEP_NAMES.get(sep, sep)}")
            self._control._separator = sep
            self._control._separator_label.show()
        else:
            self._control._separator = None
            self._control._separator_label.hide()
        self._model_type = model.type
        if ext := model.extension_default:
            self._extension_default = ext
        return None

    @validate_protocol
    def to_model(self) -> WidgetDataModel[np.ndarray]:
        meta = self._prep_table_meta()
        if sep := self._control._separator:
            meta.separator = sep
        # NOTE: if this model is passed to another widget and modified in this widget,
        # the other array will be modified as well. To avoid this, we need to reset the
        # copy-on-write state of this array.
        self.model()._is_original_array = True
        return WidgetDataModel(
            value=self.model()._arr,
            type=self.model_type(),
            extension_default=self._extension_default,
            metadata=meta,
        )

    @validate_protocol
    def model_type(self):
        return self._model_type

    @validate_protocol
    def update_configs(self, cfg: SpreadsheetConfigs):
        self.horizontalHeader().setDefaultSectionSize(cfg.default_cell_width)
        self.verticalHeader().setDefaultSectionSize(cfg.default_cell_height)
        self._sep_on_copy = cfg.separator_on_copy.encode().decode("unicode_escape")

    @validate_protocol
    def is_modified(self) -> bool:
        if self._modified_override is not None:
            return self._modified_override
        return self._undo_stack.undoable()

    @validate_protocol
    def set_modified(self, value: bool) -> None:
        self._modified_override = value

    @validate_protocol
    def is_editable(self) -> bool:
        return self.editTriggers() == Editability.TRUE

    @validate_protocol
    def set_editable(self, value: bool) -> None:
        if value:
            trig = Editability.TRUE
        else:
            trig = Editability.FALSE
        self.setEditTriggers(trig)

    @validate_protocol
    def control_widget(self) -> QTableControl:
        return self._control

    @validate_protocol
    def theme_changed_callback(self, theme: Theme) -> None:
        if self._control:
            self._control.update_theme(theme)

    def array_update(
        self,
        index: tuple[int | slice, int | slice],
        value: str,
        *,
        record_undo: bool = True,
    ) -> None:
        """Update the data at the given index."""
        r, c = index
        arr = self.model()._arr
        _ud_old_shape = arr.shape
        r_max = r.stop - 1 if isinstance(r, slice) else r
        c_max = c.stop - 1 if isinstance(c, slice) else c
        if r_max >= arr.shape[0] or c_max >= arr.shape[1]:  # need expansion
            _ud_old_data = ""
            _ud_old_shape = arr.shape
            self.array_expand(r_max + 1, c_max + 1)
            _ud_new_shape = arr.shape
            _action_reshape = ReshapeAction(_ud_old_shape, _ud_new_shape)
            arr = self.model()._arr
        else:
            if isinstance(r, slice) or isinstance(c, slice):
                _ud_old_data = arr[r, c].copy()
            else:
                _ud_old_data = arr[r, c]
            _action_reshape = None
        if self.model()._is_original_array:
            self.model()._arr = arr = arr.copy()
        arr[r, c] = value
        _ud_new_data = arr[r, c]
        _action = EditAction(_ud_old_data, _ud_new_data, (r, c))
        if _action_reshape is not None:
            _action = ActionGroup([_action_reshape, _action])
        if record_undo:
            self._undo_stack.push(_action)

    def array_expand(self, nr: int, nc: int):
        """Expand the array to the given shape (nr, nc)."""
        # ReshapeAction must be recorded outside this function.
        old_arr = self.model()._arr
        nr0, nc0 = old_arr.shape
        new_arr = np.pad(
            old_arr,
            [(0, max(nr - nr0, 0)), (0, max(nc - nc0, 0))],
            mode="constant",
            constant_values="",
        )
        self.model().set_array(new_arr, is_original=False)
        self._control.update_for_table(self)
        self.update()

    def array_shrink(self, nr: int, nc: int):
        """Shrink the array to the given shape."""
        # slicing returns the view of the array, so it should be marked as original.
        self.model().set_array(self.model()._arr[:nr, :nc], is_original=True)
        self._control.update_for_table(self)
        self.update()

    def array_insert(
        self,
        index: int,
        axis: Literal[0, 1],
        values: np.ndarray | None = None,
        *,
        record_undo: bool = True,
    ) -> None:
        """Insert an empty array at the given index."""
        self.model().set_array(
            np.insert(
                self.model()._arr,
                index,
                "" if values is None else values,
                axis=axis,
            ),
            is_original=False,
        )
        if record_undo:
            self._undo_stack.push(InsertAction(index, axis, values))
        self.update()

    def array_delete(
        self,
        indices: Iterable[int],
        axis: Literal[0, 1],
        *,
        record_undo: bool = True,
    ):
        """Remove the array at the given index."""
        # Make action group that remove the row/column one by one. Here, indices may be
        # out of range, as this widget is a spreadsheet.
        size_of_axis = self.model()._arr.shape[axis]
        indices = list(indices)
        _action = ActionGroup(
            [
                RemoveAction(idx, axis, self.model()._arr[_sl(idx, axis)].copy())
                for idx in sorted(indices, reverse=True)
                if idx < size_of_axis
            ]
        )
        # Update the underlying array data and redraw the table.
        self.model().set_array(
            np.delete(self.model()._arr, list(indices), axis=axis), is_original=False
        )
        self.update()
        # Record the action if necessary.
        if record_undo:
            self._undo_stack.push(_action)

    def undo(self):
        """Undo the last action."""
        if action := self._undo_stack.undo():
            action.invert().apply(self)
            self.update()

    def redo(self):
        """Redo the last undone action."""
        if action := self._undo_stack.redo():
            action.apply(self)
            self.update()

    def _make_context_menu(self):
        menu = QtW.QMenu(self)
        menu.addAction("Cut", self._cut_and_copy_to_clipboard)
        menu.addAction("Copy", self._copy_to_clipboard)
        copy_as_menu = menu.addMenu("Copy As ...")
        copy_as_menu.addAction("CSV", self._copy_as_csv)
        copy_as_menu.addAction("Markdown", self._copy_as_markdown)
        copy_as_menu.addAction("HTML", self._copy_as_html)
        copy_as_menu.addAction("rST", self._copy_as_rst)
        menu.addAction("Paste", self._paste_from_clipboard)
        menu.addSeparator()
        menu.addAction("Insert Row Above", self._insert_row_above)
        menu.addAction("Insert Row Below", self._insert_row_below)
        menu.addAction("Insert Column Left", self._insert_column_left)
        menu.addAction("Insert Column Right", self._insert_column_right)
        menu.addSeparator()
        menu.addAction("Remove Selected Rows", self._remove_selected_rows)
        menu.addAction("Remove Selected Columns", self._remove_selected_columns)
        menu.addSeparator()
        menu.addAction("Measure At Selection", self._measure)
        return menu

    def _cut_and_copy_to_clipboard(self):
        self._copy_to_clipboard()
        self._delete_selection()

    def _copy_to_clipboard(self, format="TSV"):
        sels = self._selection_model.ranges
        if len(sels) != 1:
            return
        sel = sels[0]
        values = self.model()._arr[sel]
        if values.size > 0:
            string = table_to_text(values, format=format)[0]
            QtW.QApplication.clipboard().setText(string)

    def _copy_as_csv(self):
        return self._copy_to_clipboard("CSV")

    def _copy_as_markdown(self):
        return self._copy_to_clipboard("Markdown")

    def _copy_as_html(self):
        return self._copy_to_clipboard("HTML")

    def _copy_as_rst(self):
        return self._copy_to_clipboard("rST")

    def _paste_from_clipboard(self):
        text = QtW.QApplication.clipboard().text()
        if not text:
            return

        buf = StringIO(text)
        arr_paste = np.loadtxt(
            buf, dtype=np.dtypes.StringDType(), delimiter="\t", ndmin=2
        )
        # undo info
        _ud_old_shape = self.data_shape()

        sl0, sl1, _ud_old_data = self._paste_array(arr_paste)

        # undo info
        _ud_new_shape = self.data_shape()
        _ud_new_data = arr_paste.copy()
        _action_edit = EditAction(_ud_old_data, _ud_new_data, (sl0, sl1))
        if _ud_old_shape == _ud_new_shape:
            _action = _action_edit
        else:
            _action_reshape = ReshapeAction(_ud_old_shape, _ud_new_shape)
            _action = ActionGroup([_action_reshape, _action_edit])
        self._undo_stack.push(_action)

    def _paste_array(self, arr_paste: np.ndarray) -> tuple[slice, slice, np.ndarray]:
        """Update the array and return the pasteed range and old data."""
        arr = self.model()._arr
        # paste in the text
        rng = self._selection_model.get_single_range()
        row0, col0 = rng[0].start, rng[1].start
        lr = max(arr_paste.shape[0], rng[0].stop - rng[0].start)
        lc = max(arr_paste.shape[1], rng[1].stop - rng[1].start)

        # expand the table if necessary
        expanded = False
        if (row0 + lr) > arr.shape[0]:
            arr = np.pad(
                arr,
                [(0, row0 + lr - arr.shape[0]), (0, 0)],
                mode="constant",
                constant_values="",
            )
            expanded = True
        if (col0 + lc) > arr.shape[1]:
            arr = np.pad(
                arr,
                [(0, 0), (0, col0 + lc - arr.shape[1])],
                mode="constant",
                constant_values="",
            )
            expanded = True
        if not expanded:
            arr = arr.copy()
        # paste the data
        target_slice = (slice(row0, row0 + lr), slice(col0, col0 + lc))
        old_data = arr[target_slice].copy()
        arr[target_slice] = arr_paste
        self.model().set_array(arr, is_original=False)

        # select what was just pasted
        self._selection_model.set_ranges([target_slice])
        self.update()
        return target_slice + (old_data,)

    def _delete_selection(self):
        _actions = []
        _maybe_empty_edges = False
        arr = self.model()._arr
        # replace all the selected cells with empty strings.
        for sel in self._selection_model.ranges:
            old_array = arr[sel].copy()
            new_array = np.zeros_like(old_array)
            _actions.append(EditAction(old_array, new_array, sel))
            arr[sel] = ""
            if sel[0].stop == arr.shape[0] or sel[1].stop == arr.shape[1]:
                _maybe_empty_edges = True
        # if this deletion makes the array edges empty, array should be shrunk.
        if _maybe_empty_edges:
            arr_nchars = np.char.str_len(arr)
            size_0 = _size_to_shrink(np.max(arr_nchars, axis=1))
            size_1 = _size_to_shrink(np.max(arr_nchars, axis=0))
            if size_0 < arr_nchars.shape[0] or size_1 < arr_nchars.shape[1]:
                self.array_shrink(size_0, size_1)
                _actions.append(ReshapeAction(arr_nchars.shape, (size_0, size_1)))
        self.update()
        self._undo_stack.push(ActionGroup(_actions))

    def _insert_row_below(self):
        """Insert a row below the current selection."""
        self.array_insert(self._selection_model.current_index.row + 1, 0)

    def _insert_row_above(self):
        """Insert a row above the current selection."""
        self.array_insert(self._selection_model.current_index.row, 0)

    def _insert_column_right(self):
        """Insert a column to the right of the current selection."""
        self.array_insert(self._selection_model.current_index.column + 1, 1)

    def _insert_column_left(self):
        """Insert a column to the left of the current selection."""
        self.array_insert(self._selection_model.current_index.column, 1)

    def _remove_selected_rows(self):
        """Remove the selected rows."""
        selected_rows = set[int]()
        for sel in self._selection_model.ranges:
            selected_rows.update(range(sel[0].start, sel[0].stop))
        self.array_delete(selected_rows, axis=0)

    def _remove_selected_columns(self):
        """Remove the selected columns."""
        selected_cols = set[int]()
        for sel in self._selection_model.ranges:
            selected_cols.update(range(sel[1].start, sel[1].stop))
        self.array_delete(selected_cols, axis=1)

    def _measure(self):
        ui = get_main_window(self)
        ui.exec_action("builtins:table:measure-selection")

    def keyPressEvent(self, e: QtGui.QKeyEvent):
        _Ctrl = QtCore.Qt.KeyboardModifier.ControlModifier
        if e.modifiers() & _Ctrl and e.key() == QtCore.Qt.Key.Key_C:
            return self._copy_to_clipboard()
        elif e.modifiers() & _Ctrl and e.key() == QtCore.Qt.Key.Key_V:
            return self._paste_from_clipboard()
        elif e.modifiers() & _Ctrl and e.key() == QtCore.Qt.Key.Key_X:
            return self._cut_and_copy_to_clipboard()
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
            if qindex.isValid():
                self.edit(qindex)
                if editor := self.itemDelegate()._current_editor_ref():
                    editor.setText(e.text())
                return
        return super().keyPressEvent(e)

    if TYPE_CHECKING:

        def model(self) -> QStringArrayModel: ...


_R_CENTER = QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter


class QTableControl(QtW.QWidget):
    def __init__(self, table: QSpreadsheet):
        super().__init__()
        layout = QtW.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(_R_CENTER)
        self._info_label = QtW.QLabel("")
        self._info_label.setAlignment(_R_CENTER)

        # toolbuttons
        groupbox_ins = QToolButtonGroup(self)
        groupbox_rem = QToolButtonGroup(self)
        _btn_ins = groupbox_ins.add_widgets(
            _tool_btn(table._insert_row_above, "row_insert_top"),
            _tool_btn(table._insert_row_below, "row_insert_bottom"),
            _tool_btn(table._insert_column_left, "col_insert_left"),
            _tool_btn(table._insert_column_right, "col_insert_right"),
        )
        _btn_rem = groupbox_rem.add_widgets(
            _tool_btn(table._remove_selected_rows, "row_remove"),
            _tool_btn(table._remove_selected_columns, "col_remove"),
        )
        self._tool_buttons: list[QtW.QToolButton] = _btn_ins + _btn_rem
        self._separator_label = QtW.QLabel()
        self._separator: str | None = None

        empty = QtW.QWidget()
        empty.setSizePolicy(
            QtW.QSizePolicy.Policy.Expanding, QtW.QSizePolicy.Policy.Preferred
        )
        layout.addWidget(empty)  # empty space
        layout.addWidget(self._info_label)
        layout.addWidget(self._separator_label)
        layout.addWidget(groupbox_ins)
        layout.addWidget(groupbox_rem)
        layout.addWidget(QSelectionRangeEdit(table))

    def update_for_table(self, table: QSpreadsheet):
        shape = table.model()._arr.shape
        self._info_label.setText(f"Shape: {shape!r}")

    def update_theme(self, theme: Theme):
        """Update the theme of the control."""
        color = theme.foreground
        for btn in self._tool_buttons:
            icon_path = btn.property("icon_path")
            btn.setIcon(QColoredSVGIcon.fromfile(icon_path, color))


def _sl(idx: int, axis: Literal[0, 1]) -> tuple:
    if axis == 0:
        return idx, slice(None)
    else:
        return slice(None), idx


_ICON_PATH = Path(__file__).parent.parent.parent / "resources"


def _tool_btn(callback, icon: str) -> QtW.QToolButton:
    """Create a tool button with the given icon and callback."""
    btn = QtW.QToolButton()
    icon_path = _ICON_PATH / f"{icon}.svg"
    btn.setProperty("icon_path", icon_path)
    btn.setToolTip(callback.__doc__)
    btn.clicked.connect(callback)
    return btn


class QToolButtonGroup(QtW.QGroupBox):
    """A group of tool buttons with a horizontal layout."""

    def __init__(self, parent: QtW.QWidget | None = None):
        super().__init__(parent)
        self.setStyleSheet("QToolButtonGroup {margin: 0px;}")
        self.setLayout(QtW.QHBoxLayout(self))
        self.layout().setContentsMargins(0, 0, 0, 0)

        inner = QtW.QWidget()
        inner_layout = QtW.QHBoxLayout(inner)
        self.setContentsMargins(0, 0, 0, 0)
        inner_layout.setContentsMargins(0, 0, 0, 0)
        inner_layout.setSpacing(1)
        self._inner_layout = inner_layout
        self.layout().addWidget(inner)

    def add_widgets(self, *widgets: QtW.QWidget):
        """Add a widget to the group."""
        for widget in widgets:
            self._inner_layout.addWidget(widget)
        return widgets


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
    """A char version of np.arange.

    Examples
    --------
    ``` python
    char_arange(3)  # array(["A", "B", "C"])
    char_arange(25, 28)  # array(["Z", "AA", "AB"])
    ```
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


def _size_to_shrink(proj: NDArray[np.intp]) -> int:
    """Determine the number of rows/columns array should be shrunk to.

    >>> _num_to_shrink(np.array([4, 3, 0, 0]))  # 2
    >>> _num_to_shrink(np.array([4, 3, 6, 0]))  # 3
    >>> _num_to_shrink(np.array([4, 3]))  # 2
    """
    _len = proj.size
    for i in range(_len - 1, -1, -1):
        if proj[i] != 0:
            return i + 1
    return _len


@dataclass
class SpreadsheetConfigs:
    default_cell_width: int = config_field(
        default=75,
        tooltip="Default width (pixel) of cells.",
    )
    default_cell_height: int = config_field(
        default=22,
        tooltip="Default height (pixel) of cells.",
    )
    separator_on_copy: str = config_field(
        default="\\t",
        tooltip="Separator used when the content of table is copied to the clipboard.",
    )
