from __future__ import annotations
from typing import Any

from qtpy import QtWidgets as QtW
from qtpy import QtGui, QtCore
from himena.consts import StandardType
from himena.types import WidgetDataModel
from himena.model_meta import TableMeta
from himena.builtins.qt.widgets._table_base import QTableBase, QSelectionRangeEdit


class QDefaultTableWidget(QtW.QTableWidget, QTableBase):
    def __init__(self):
        QtW.QTableWidget.__init__(self)
        QTableBase.__init__(self)
        self._edit_trigger = self.editTriggers()
        self._control = QTableControl(self)

        @self.itemChanged.connect
        def _():
            self._modified = True

    def update_model(self, model: WidgetDataModel[list[list[Any]]]) -> None:
        import numpy as np

        table = np.asarray(model.value, dtype=str)
        self.setRowCount(table.shape[0])
        self.setColumnCount(table.shape[1])
        for i in range(self.rowCount()):
            for j in range(self.columnCount()):
                self.setItem(i, j, QtW.QTableWidgetItem(table[i, j]))
        if isinstance(meta := model.additional_data, TableMeta):
            if (pos := meta.current_position) is not None:
                self.setCurrentCell(*pos)
            for (r0, r1), (c0, c1) in meta.selections:
                rng = QtW.QTableWidgetSelectionRange(r0, c0 - 1, r1, c1 - 1)
                self.setRangeSelected(rng, True)
        self._relabel_headers()
        self._modified = False
        self._control.update_for_table(self)
        return None

    def to_model(self) -> WidgetDataModel[list[list[Any]]]:
        return WidgetDataModel(
            value=self._to_list(
                slice(0, self.rowCount()), slice(0, self.columnCount())
            ),
            type=self.model_type(),
            extension_default=".csv",
            additional_data=self._prep_table_meta(),
        )

    def _relabel_headers(self):
        self.setVerticalHeaderLabels([str(i) for i in range(self.rowCount())])
        self.setHorizontalHeaderLabels([str(i) for i in range(self.columnCount())])

    def model_type(self):
        return StandardType.TABLE

    def is_modified(self) -> bool:
        return self._modified

    def set_modified(self, value: bool) -> None:
        self._modified = value

    def set_editable(self, value: bool) -> None:
        if value:
            trig = self._edit_trigger
        else:
            trig = QtW.QAbstractItemView.EditTrigger.NoEditTriggers
        self.setEditTriggers(trig)

    def control_widget(self) -> QTableControl:
        return self._control

    def _to_list(self, rsl: slice, csl: slice) -> list[list[str]]:
        values: list[list[str]] = []
        for r in range(rsl.start, rsl.stop):
            cells: list[str] = []
            for c in range(csl.start, csl.stop):
                item = self.item(r, c)
                if item is not None:
                    cells.append(item.text())
                else:
                    cells.append("")
            values.append(cells)
        return values

    def _copy_to_clipboard(self):
        selranges = self.selectedRanges()
        if not selranges:
            return
        if len(selranges) > 1:
            return

        # copy first selection range
        sel = selranges[0]
        values = self._to_list(
            slice(sel.topRow(), sel.bottomRow() + 1),
            slice(sel.leftColumn(), sel.rightColumn() + 1),
        )
        if values:
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

        # paste in the text
        row0, col0 = idx.row(), idx.column()
        data = [line.split("\t") for line in text.splitlines()]
        # expand the table if necessary
        needs_relabel = False
        if (row0 + len(data)) > self.rowCount():
            self.setRowCount(row0 + len(data))
            needs_relabel = True
        if data and (col0 + len(data[0])) > self.columnCount():
            self.setColumnCount(col0 + len(data[0]))
            needs_relabel = True
        if needs_relabel:
            self._relabel_headers()
        # paste the data
        for r, line in enumerate(data):
            for c, cell in enumerate(line):
                try:
                    self.item(row0 + r, col0 + c).setText(str(cell))
                except AttributeError:
                    self.setItem(row0 + r, col0 + c, QtW.QTableWidgetItem(str(cell)))

        # select what was just pasted
        selrange = QtW.QTableWidgetSelectionRange(row0, col0, row0 + r, col0 + c)
        self.clearSelection()
        self.setRangeSelected(selrange, True)

    def _delete_selection(self):
        for item in self.selectedItems():
            item.setText("")

    def _insert_row_below(self):
        row = self.currentRow()
        self.insertRow(row + 1)
        self._relabel_headers()

    def _insert_row_above(self):
        row = self.currentRow()
        self.insertRow(row)
        self._relabel_headers()

    def _insert_column_right(self):
        col = self.currentColumn()
        self.insertColumn(col + 1)
        self._relabel_headers()

    def _insert_column_left(self):
        col = self.currentColumn()
        self.insertColumn(col)
        self._relabel_headers()

    def _delete_selected_rows(self):
        for row in sorted({i.row() for i in self.selectedItems()}, reverse=True):
            self.removeRow(row)
        self._relabel_headers()

    def _delete_selected_columns(self):
        for col in sorted({i.column() for i in self.selectedItems()}, reverse=True):
            self.removeColumn(col)
        self._relabel_headers()

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
        return super().keyPressEvent(e)


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
        self._insert_menu_button.setText("Insert")  # or "icons8:plus"
        self._insert_menu_button.setMenu(self._make_insert_menu(table))
        self._remove_menu_button = QtW.QPushButton()
        self._remove_menu_button.setText("Remove")
        self._remove_menu_button.setMenu(self._make_remove_menu(table))

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
        self._label.setText(f"Shape ({table.rowCount()}, {table.columnCount()})")
        return None

    def _make_insert_menu(self, table: QDefaultTableWidget):
        menu = QtW.QMenu(self)
        menu.addAction("Row above", table._insert_row_above)
        menu.addAction("Row below", table._insert_row_below)
        menu.addAction("Column left", table._insert_column_left)
        menu.addAction("Column right", table._insert_column_right)
        return menu

    def _make_remove_menu(self, table: QDefaultTableWidget):
        menu = QtW.QMenu(self)
        menu.addAction("Rows", table._delete_selected_rows)
        menu.addAction("Columns", table._delete_selected_columns)
        return menu
