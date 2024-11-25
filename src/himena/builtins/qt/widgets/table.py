from __future__ import annotations

from enum import Enum, auto
from io import StringIO
from typing import TYPE_CHECKING, Any
import numpy as np

from qtpy import QtWidgets as QtW
from qtpy import QtGui, QtCore
from qtpy.QtCore import Qt

from himena.consts import StandardType
from himena.types import WidgetDataModel
from himena.model_meta import TableMeta
from himena.plugins import protocol_override
from himena.builtins.qt.widgets._table_base import QTableBase, QSelectionRangeEdit


class HeaderFormat(Enum):
    """Enum of how to index table header."""

    NumberZeroIndexed = auto()
    NumberOneIndexed = auto()
    Alphabetic = auto()


_FLAGS = (
    Qt.ItemFlag.ItemIsEnabled
    | Qt.ItemFlag.ItemIsSelectable
    | Qt.ItemFlag.ItemIsEditable
)


class QStringArrayModel(QtCore.QAbstractTableModel):
    """Table model for a string array."""

    def __init__(self, arr: np.ndarray, parent=None):
        super().__init__(parent)
        self._arr = arr  # 2D
        if arr.ndim != 2:
            raise ValueError("Only 2D array is supported.")
        if not isinstance(arr.dtype, np.dtypes.StringDType):
            raise ValueError("Only string array is supported.")
        self._nrows, self._ncols = arr.shape
        self._header_format = HeaderFormat.NumberZeroIndexed

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
            r, c = index.row(), index.column()
            if r >= self._arr.shape[0] or c >= self._arr.shape[1]:
                self._arr = np.pad(
                    self._arr,
                    [
                        (0, max(r - self._arr.shape[0] + 1, 0)),
                        (0, max(c - self._arr.shape[1] + 1, 0)),
                    ],
                    mode="constant",
                    constant_values="",
                )
            self._arr[r, c] = str(value)
            self.dataChanged.emit(index, index)
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


class QDefaultTableWidget(QTableBase):
    HeaderFormat = HeaderFormat

    def __init__(self):
        QTableBase.__init__(self)
        self.setEditTriggers(_EDITABLE)
        self._control = None
        self._modified = False

    def setHeaderFormat(self, value: HeaderFormat) -> None:
        if model := self.model():
            model._header_format = value

    @protocol_override
    def update_model(self, model: WidgetDataModel[np.ndarray]) -> None:
        if model.value is None:
            table = np.empty((0, 0), dtype=np.dtypes.StringDType())
        else:
            table = np.asarray(model.value, dtype=np.dtypes.StringDType())
        self.setModel(QStringArrayModel(table))
        if isinstance(meta := model.additional_data, TableMeta):
            if (pos := meta.current_position) is not None:
                index = self.model().index(*pos)
                self.setCurrentIndex(index)
            if smod := self.selectionModel():
                for (r0, r1), (c0, c1) in meta.selections:
                    index_top_left = self.model().index(r0, c0)
                    index_bottom_right = self.model().index(r1, c1)
                    sel = QtCore.QItemSelection(index_top_left, index_bottom_right)
                    smod.select(sel, QtCore.QItemSelectionModel.SelectionFlag.Select)

        self.update()
        self._modified = False
        if self._control is None:
            self._control = QTableControl(self)
        self._control.update_for_table(self)
        self.model().dataChanged.connect(self.set_modified)
        return None

    @protocol_override
    def to_model(self) -> WidgetDataModel[np.ndarray]:
        return WidgetDataModel(
            value=self.model()._arr,
            type=self.model_type(),
            extension_default=".csv",
            additional_data=self._prep_table_meta(),
        )

    @protocol_override
    def model_type(self):
        return StandardType.TABLE

    @protocol_override
    def is_modified(self) -> bool:
        return self._modified

    @protocol_override
    def set_modified(self, value: bool) -> None:
        self._modified = value

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

    def _selections_as_slices(self) -> list[tuple[slice, slice]]:
        selranges = self.selectionModel().selection()
        if selranges.count() != 1:
            return

        out = []
        for isel in range(selranges.count()):
            sel = selranges[isel]
            sl = (
                slice(sel.top(), sel.bottom() + 1),
                slice(sel.left(), sel.right() + 1),
            )
            out.append(sl)
        return out

    def _copy_to_clipboard(self):
        sels = self._selections_as_slices()
        if len(sels) != 1:
            return
        sel = sels[0]
        values = self.model()._arr[sel]
        if values.size > 0:
            string = "\n".join(["\t".join(cells) for cells in values])
            QtW.QApplication.clipboard().setText(string)

    def _paste_from_clipboard(self):
        sel_idx = self.selectedIndexes()
        if sel_idx:
            idx = sel_idx[0]
        else:
            idx = self.currentIndex()
        text = QtW.QApplication.clipboard().text()
        if not text:
            return

        arr = self.model()._arr
        # paste in the text
        row0, col0 = idx.row(), idx.column()
        buf = StringIO(text)
        arr_paste = np.loadtxt(
            buf, dtype=np.dtypes.StringDType(), delimiter="\t", ndmin=2
        )
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

        # select what was just pasted
        topleft = self.model().index(row0, col0)
        bottomright = self.model().index(row0 + lr - 1, col0 + lc - 1)
        item_selection = QtCore.QItemSelection(topleft, bottomright)
        self.clearSelection()
        self.selectionModel().select(
            item_selection, QtCore.QItemSelectionModel.SelectionFlag.Select
        )

        self.update()

    def _delete_selection(self):
        for sel in self._selections_as_slices():
            self.model()._arr[sel] = ""

    def _insert_row_below(self):
        row = self.currentIndex().row()
        arr = self.model()._arr
        arr = np.insert(arr, row + 1, "", axis=0)
        self.model()._arr = arr

    def _insert_row_above(self):
        row = self.currentIndex().row()
        arr = self.model()._arr
        arr = np.insert(arr, row, "", axis=0)
        self.model()._arr = arr

    def _insert_column_right(self):
        col = self.currentIndex().column()
        arr = self.model()._arr
        arr = np.insert(arr, col + 1, "", axis=1)
        self.model()._arr = arr

    def _insert_column_left(self):
        col = self.currentIndex().column()
        arr = self.model()._arr
        arr = np.insert(arr, col, "", axis=1)
        self.model()._arr = arr

    def _remove_selected_rows(self):
        selected_rows = set[int]()
        for sel in self._selections_as_slices():
            selected_rows.update(range(sel[0].start, sel[0].stop))
        self.model()._arr = np.delete(self.model()._arr, list(selected_rows), axis=0)

    def _remove_selected_columns(self):
        selected_cols = set[int]()
        for sel in self._selections_as_slices():
            selected_cols.update(range(sel[1].start, sel[1].stop))
        self.model()._arr = np.delete(self.model()._arr, list(selected_cols), axis=1)

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
        elif (
            (not (e.modifiers() & _Ctrl))
            and (
                e.modifiers() == QtCore.Qt.KeyboardModifier.NoModifier
                or e.modifiers() & QtCore.Qt.KeyboardModifier.ShiftModifier
            )
            and Qt.Key.Key_Space <= e.key() <= Qt.Key.Key_ydiaeresis
        ):
            self.edit(self.currentIndex())
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

        empty = QtW.QWidget()
        empty.setSizePolicy(
            QtW.QSizePolicy.Policy.Expanding, QtW.QSizePolicy.Policy.Preferred
        )
        layout.addWidget(empty)  # empty space
        layout.addWidget(self._label)
        layout.addWidget(self._insert_menu_button)
        layout.addWidget(self._remove_menu_button)
        layout.addWidget(QSelectionRangeEdit(table))

    def update_for_table(self, table: QDefaultTableWidget):
        shape = table.model()._arr.shape
        self._label.setText(f"Shape {shape!r}")
        return None

    def _make_insert_menu(self, table: QDefaultTableWidget):
        menu = QtW.QMenu(self)
        menu.addAction("Row above", table._insert_row_above)
        menu.addAction("Row below", table._insert_row_below)
        menu.addAction("Column left", table._insert_column_left)
        menu.addAction("Column right", table._insert_column_right)
        return menu

    def _make_delete_menu(self, table: QDefaultTableWidget):
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
