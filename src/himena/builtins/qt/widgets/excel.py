from __future__ import annotations

from typing import TYPE_CHECKING

from qtpy import QtWidgets as QtW, QtCore
from himena.model_meta import ExcelMeta
from himena.qt._qrename import QTabRenameLineEdit
from himena.builtins.qt.widgets.table import QDefaultTableWidget
from himena.builtins.qt.widgets._table_base import QSelectionRangeEdit
from himena.types import WidgetDataModel
from himena.consts import StandardType

_EDIT_DISABLED = QtW.QAbstractItemView.EditTrigger.NoEditTriggers
_EDIT_ENABLED = (
    QtW.QAbstractItemView.EditTrigger.DoubleClicked
    | QtW.QAbstractItemView.EditTrigger.EditKeyPressed
)


class QExcelSheet(QDefaultTableWidget):
    def _relabel_headers(self):
        # A, B, ..., Z, AA, AB, ...
        chars = char_arange(self.columnCount())
        self.setHorizontalHeaderLabels(chars.tolist())


class QExcelTableStack(QtW.QTabWidget):
    def __init__(self):
        super().__init__()
        self._edit_trigger = _EDIT_ENABLED
        self._control = QExcelTableStackControl()
        self.currentChanged.connect(self._on_tab_changed)
        self._line_edit = QTabRenameLineEdit(self, allow_duplicate=False)

    def _on_tab_changed(self, index: int):
        self._control.update_for_table(self.widget(index))
        return None

    def update_model(self, model: WidgetDataModel[dict[str, list[list[str]]]]):
        self.clear()
        for sheet_name, table in model.value.items():
            table_widget = QExcelSheet()
            table_widget.update_model(
                WidgetDataModel(value=table, type=StandardType.TABLE)
            )
            self.addTab(table_widget, sheet_name)
        if self.count() > 0:
            self.setCurrentIndex(0)
            self._control.update_for_table(self.widget(0))
        return None

    def to_model(self) -> WidgetDataModel[dict[str, list[list[str]]]]:
        index = self.currentIndex()
        table_meta = self.widget(index)._prep_table_meta()
        return WidgetDataModel(
            value={
                self.tabText(i): self.widget(i).to_model().value
                for i in range(self.count())
            },
            type=self.model_type(),
            extension_default=".xlsx",
            additional_data=ExcelMeta(
                current_position=table_meta.current_position,
                selections=table_meta.selections,
                current_sheet=self.tabText(index),
            ),
        )

    def control_widget(self) -> QExcelTableStackControl:
        return self._control

    def model_type(self):
        return StandardType.EXCEL

    def is_modified(self) -> bool:
        return any(self.widget(i).is_modified() for i in range(self.count()))

    def set_modified(self, value: bool) -> None:
        for i in range(self.count()):
            self.widget(i).set_modified(value)

    def size_hint(self) -> tuple[int, int]:
        return 400, 300

    def is_editable(self) -> bool:
        return self._edit_trigger == _EDIT_ENABLED

    def set_editable(self, value: bool) -> None:
        self._edit_trigger = _EDIT_ENABLED if value else _EDIT_DISABLED
        for i in range(self.count()):
            self.widget(i).set_editable(value)

    if TYPE_CHECKING:

        def widget(self, index: int) -> QDefaultTableWidget: ...


_R_CENTER = QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter


class QExcelTableStackControl(QtW.QWidget):
    def __init__(self):
        super().__init__()
        layout = QtW.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(_R_CENTER)
        self._value_line_edit = QtW.QLineEdit()
        self._label = QtW.QLabel("")
        self._label.setAlignment(_R_CENTER)
        self._selection_range = QSelectionRangeEdit()
        layout.addWidget(self._value_line_edit)
        layout.addWidget(self._label)
        layout.addWidget(self._selection_range)
        self._value_line_edit.editingFinished.connect(self.update_for_editing)

    def update_for_table(self, table: QDefaultTableWidget):
        model = table.model()
        self._label.setText(f"Shape ({model.rowCount()}, {model.columnCount()})")
        self._selection_range.connect_table(table)
        table.selectionModel().currentChanged.connect(self.update_for_current_index)
        self.update_for_current_index(table.currentIndex())
        return None

    def update_for_current_index(self, index: QtCore.QModelIndex):
        qtable = self._selection_range._qtable
        if qtable is None:
            return None
        self._value_line_edit.setText(qtable.model().data(index))
        return None

    def update_for_editing(self):
        qtable = self._selection_range._qtable
        if qtable is None:
            return None
        text = self._value_line_edit.text()
        qtable.model().setData(qtable.currentIndex(), text)
        qtable.setFocus()
        return None


ORD_A = ord("A")
CHARS = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ") + [""]
LONGEST = CHARS[:-1]


def _iter_char(start: int, stop: int):
    import numpy as np

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
    import numpy as np

    global LONGEST
    if stop is None:
        start, stop = 0, start
    nmax = len(LONGEST)
    if stop <= nmax:
        return np.array(LONGEST[start:stop], dtype="<U4")
    LONGEST = np.append(LONGEST, np.fromiter(_iter_char(nmax, stop), dtype="<U4"))
    return LONGEST[start:].copy()
