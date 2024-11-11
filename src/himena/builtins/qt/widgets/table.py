from __future__ import annotations
from typing import Any

from qtpy import QtWidgets as QtW
from qtpy import QtGui, QtCore
from himena.consts import StandardTypes
from himena.types import WidgetDataModel
from himena.model_meta import TableMeta
from himena.qt._qfinderwidget import QTableFinderWidget


class QDefaultTableWidget(QtW.QTableWidget):
    def __init__(self):
        super().__init__()
        self._edit_trigger = self.editTriggers()
        self._modified = False
        self.horizontalHeader().setFixedHeight(18)
        self._finder_widget = None

        # scroll by pixel
        self.setVerticalScrollMode(QtW.QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.setHorizontalScrollMode(QtW.QAbstractItemView.ScrollMode.ScrollPerPixel)
        # scroll bar policy
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        @self.itemChanged.connect
        def _():
            self._modified = True

    def update_model(self, model: WidgetDataModel):
        import numpy as np

        table = np.asarray(model.value, dtype=str)
        self.setRowCount(table.shape[0])
        self.setColumnCount(table.shape[1])
        for i in range(self.rowCount()):
            for j in range(self.columnCount()):
                self.setItem(i, j, QtW.QTableWidgetItem(table[i, j]))
            self.setRowHeight(i, 22)
        if isinstance(meta := model.additional_data, TableMeta):
            if (pos := meta.current_position) is not None:
                self.setCurrentCell(*pos)
            for r, c in meta.selections:
                self.setRangeSelected(QtW.QTableWidgetSelectionRange(*r, *c), True)
        self._modified = False
        return None

    def to_model(self) -> WidgetDataModel[list[list[Any]]]:
        return WidgetDataModel(
            value=self._to_list(
                slice(0, self.rowCount()), slice(0, self.columnCount())
            ),
            type=self.model_type(),
            extension_default=".csv",
            additional_data=TableMeta(
                current_position=(self.currentRow(), self.currentColumn()),
                selections=[_sel_range_to_slices(r) for r in self.selectedRanges()],
            ),
        )

    def model_type(self):
        return StandardTypes.TABLE

    def size_hint(self) -> tuple[int, int]:
        return 400, 300

    def is_modified(self) -> bool:
        return self._modified

    def set_modified(self, value: bool) -> None:
        self._modified = value

    def is_editable(self) -> bool:
        return self.editTriggers() != QtW.QAbstractItemView.EditTrigger.NoEditTriggers

    def set_editable(self, value: bool) -> None:
        if value:
            trig = self._edit_trigger
        else:
            trig = QtW.QAbstractItemView.EditTrigger.NoEditTriggers
        self.setEditTriggers(trig)

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
        if not sel_idx:
            return
        text = QtW.QApplication.clipboard().text()
        if not text:
            return

        # paste in the text
        row0, col0 = sel_idx[0].row(), sel_idx[0].column()
        data = [line.split("\t") for line in text.splitlines()]
        if (row0 + len(data)) > self.rowCount():
            self.setRowCount(row0 + len(data))
        if data and (col0 + len(data[0])) > self.columnCount():
            self.setColumnCount(col0 + len(data[0]))
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

    def keyPressEvent(self, e: QtGui.QKeyEvent):
        _Ctrl = QtCore.Qt.KeyboardModifier.ControlModifier
        if e.modifiers() & _Ctrl and e.key() == QtCore.Qt.Key.Key_C:
            return self._copy_to_clipboard()
        if e.modifiers() & _Ctrl and e.key() == QtCore.Qt.Key.Key_V:
            return self._paste_from_clipboard()
        if e.modifiers() & _Ctrl and e.key() == QtCore.Qt.Key.Key_X:
            self._copy_to_clipboard()
            return self._delete_selection()
        if e.key() in (QtCore.Qt.Key.Key_Delete, QtCore.Qt.Key.Key_Backspace):
            return self._delete_selection()
        if e.modifiers() & _Ctrl and e.key() == QtCore.Qt.Key.Key_F:
            self._find_string()
            return
        return super().keyPressEvent(e)

    def _find_string(self):
        if self._finder_widget is None:
            self._finder_widget = QTableFinderWidget(self)
        self._finder_widget.show()
        self._align_finder()

    def resizeEvent(self, event):
        if self._finder_widget is not None:
            self._align_finder()
        super().resizeEvent(event)

    def _align_finder(self):
        if fd := self._finder_widget:
            vbar = self.verticalScrollBar()
            if vbar.isVisible():
                fd.move(self.width() - fd.width() - vbar.width() - 3, 5)
            else:
                fd.move(self.width() - fd.width() - 3, 5)


def _sel_range_to_slices(rng: QtW.QTableWidgetSelectionRange) -> tuple[slice, slice]:
    row = slice(rng.topRow(), rng.bottomRow() + 1)
    col = slice(rng.leftColumn(), rng.rightColumn() + 1)
    return row, col
