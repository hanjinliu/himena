from __future__ import annotations

from qtpy import QtWidgets as QtW, QtCore

from himena_builtins.qt.widgets._table_components._selection_model import Index
from himena_builtins.qt.widgets.table import QSpreadsheet
from himena_builtins.qt.widgets.dict import QDictOfWidgetEdit
from himena_builtins.qt.widgets._table_components import QSelectionRangeEdit
from himena import MainWindow
from himena.types import WidgetDataModel
from himena.consts import StandardType
from himena.plugins import validate_protocol


class QExcelEdit(QDictOfWidgetEdit):
    """Built-in Excel File Editor.

    ## Basic Usage

    This widget is used to view and edit Excel books (stack of spreadsheets). It works
    almost like a tabbed list of built-in spreadsheet for simple table types. Note that
    this widget is not designed for full replacement of Excel software. Rich text,
    formulas, and other advanced features are not supported.

    ## Drag and Drop

    Dragging a tab will provide a model of type `StandardType.TABLE` ("table").
    `Ctrl + left_button` or `middle button` are assigned to the drag event.
    """

    __himena_widget_id__ = "builtins:QExcelEdit"
    __himena_display_name__ = "Built-in Excel File Editor"

    def __init__(self, ui: MainWindow):
        super().__init__()
        self._ui = ui
        self._model_type_component = StandardType.TABLE
        self._model_type = StandardType.EXCEL
        self._control = QExcelTableStackControl()
        self._extension_default = ".xlsx"

    def _default_widget(self) -> QSpreadsheet:
        table = QSpreadsheet(self._ui)
        table.update_model(WidgetDataModel(value=None, type=StandardType.TABLE))
        table.setHeaderFormat(QSpreadsheet.HeaderFormat.Alphabetic)
        return table

    @validate_protocol
    def control_widget(self) -> QExcelTableStackControl:
        return self._control


_R_CENTER = QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter


class QExcelTableStackControl(QtW.QWidget):
    def __init__(self):
        super().__init__()
        layout = QtW.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(_R_CENTER)
        # self._header_format = QtW.QComboBox()
        # self._header_format.addItems(["0, 1, 2, ...", "1, 2, 3, ...", "A, B, C, ..."])
        self._value_line_edit = QtW.QLineEdit()
        self._label = QtW.QLabel("")
        self._label.setAlignment(_R_CENTER)
        self._selection_range = QSelectionRangeEdit()
        # layout.addWidget(self._header_format)

        # toolbuttons
        self._insert_menu_button = QtW.QPushButton()
        self._insert_menu_button.setText("Ins")  # or "icons8:plus"
        self._insert_menu_button.setMenu(self._make_insert_menu())
        self._remove_menu_button = QtW.QPushButton()
        self._remove_menu_button.setText("Rem")
        self._remove_menu_button.setMenu(self._make_delete_menu())

        layout.addWidget(self._value_line_edit)
        layout.addWidget(self._insert_menu_button)
        layout.addWidget(self._remove_menu_button)
        layout.addWidget(self._label)
        layout.addWidget(self._selection_range)
        self._value_line_edit.editingFinished.connect(self.update_for_editing)

    def update_for_component(self, table: QSpreadsheet | None):
        if table is None:
            return
        shape = table.model()._arr.shape
        self._label.setText(f"Shape {shape!r}")
        self._selection_range.connect_table(table)
        table._selection_model.moved.connect(self.update_for_current_index)
        self.update_for_current_index(
            table._selection_model.current_index, table._selection_model.current_index
        )
        return None

    @property
    def _current_table(self) -> QSpreadsheet | None:
        return self._selection_range._qtable

    def update_for_current_index(self, old: Index, new: Index):
        qtable = self._current_table
        if qtable is None:
            return None
        qindex = qtable.model().index(new.row, new.column)
        text = qtable.model().data(qindex)
        if not isinstance(text, str):
            text = ""
        self._value_line_edit.setText(text)
        return None

    def update_for_editing(self):
        qtable = self._current_table
        if qtable is None:
            return None
        text = self._value_line_edit.text()
        index = qtable._selection_model.current_index
        qindex = qtable.model().index(index.row, index.column)
        qtable.model().setData(qindex, text, QtCore.Qt.ItemDataRole.EditRole)
        qtable.setFocus()
        return None

    def _make_insert_menu(self):
        menu = QtW.QMenu(self)
        menu.addAction("Row above", self._insert_row_above)
        menu.addAction("Row below", self._insert_row_below)
        menu.addAction("Column left", self._insert_column_left)
        menu.addAction("Column right", self._insert_column_right)
        return menu

    def _make_delete_menu(self):
        menu = QtW.QMenu(self)
        menu.addAction("Rows", self._remove_selected_rows)
        menu.addAction("Columns", self._remove_selected_columns)
        return menu

    def _insert_row_above(self):
        if qtable := self._current_table:
            qtable._insert_row_above()
        return None

    def _insert_row_below(self):
        if qtable := self._current_table:
            qtable._insert_row_below()
        return None

    def _insert_column_left(self):
        if qtable := self._current_table:
            qtable._insert_column_left()
        return None

    def _insert_column_right(self):
        if qtable := self._current_table:
            qtable._insert_column_right()
        return None

    def _remove_selected_rows(self):
        if qtable := self._current_table:
            qtable._remove_selected_rows()
        return None

    def _remove_selected_columns(self):
        if qtable := self._current_table:
            qtable._remove_selected_columns()
        return None
