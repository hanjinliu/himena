from __future__ import annotations

from typing import TYPE_CHECKING, Mapping

from qtpy import QtWidgets as QtW, QtCore, QtGui

from himena_builtins.qt.widgets._table_components._selection_model import Index
from himena.standards.model_meta import ExcelMeta
from himena.qt._qrename import QTabRenameLineEdit
from himena_builtins.qt.widgets.table import QSpreadsheet
from himena_builtins.qt.widgets._table_components import QSelectionRangeEdit
from himena.types import WidgetDataModel
from himena.consts import StandardType
from himena.plugins import protocol_override

if TYPE_CHECKING:
    import numpy as np

_EDIT_DISABLED = QtW.QAbstractItemView.EditTrigger.NoEditTriggers
_EDIT_ENABLED = (
    QtW.QAbstractItemView.EditTrigger.DoubleClicked
    | QtW.QAbstractItemView.EditTrigger.EditKeyPressed
)


class QRightClickableTabBar(QtW.QTabBar):
    right_clicked = QtCore.Signal(int)

    def __init__(self, parent: QtW.QWidget | None = None) -> None:
        super().__init__(parent)
        self._last_right_clicked = None

    def mousePressEvent(self, a0: QtGui.QMouseEvent | None) -> None:
        if a0 is not None and a0.button() == QtCore.Qt.MouseButton.RightButton:
            self._last_right_clicked = self.tabAt(a0.pos())
        return super().mousePressEvent(a0)

    def mouseReleaseEvent(self, a0: QtGui.QMouseEvent | None) -> None:
        if a0 is not None and a0.button() == QtCore.Qt.MouseButton.RightButton:
            if self.tabAt(a0.pos()) == self._last_right_clicked:
                self.right_clicked.emit(self._last_right_clicked)
        self._last_right_clicked = None
        return super().mouseReleaseEvent(a0)


class QExcelFileEdit(QtW.QTabWidget):
    """Built-in Excel File Editor"""

    __himena_widget_id__ = "builtins:QExcelFileEdit"
    __himena_display_name__ = "Built-in Excel File Editor"

    def __init__(self):
        super().__init__()
        self.setTabBar(QRightClickableTabBar())
        self._edit_trigger = _EDIT_ENABLED
        self._control = QExcelTableStackControl()
        self.currentChanged.connect(self._on_tab_changed)
        self._line_edit = QTabRenameLineEdit(self, allow_duplicate=False)

        # corner widget for adding new tab
        tb = QtW.QToolButton()
        tb.setText("+")
        tb.setFont(QtGui.QFont("Arial", 12, weight=15))
        tb.setToolTip("New Tab")
        tb.clicked.connect(self._add_new_tab)
        self.setCornerWidget(tb, QtCore.Qt.Corner.TopRightCorner)
        self.tabBar().right_clicked.connect(self._tabbar_right_clicked)
        self._model_type = StandardType.EXCEL

    def _on_tab_changed(self, index: int):
        self._control.update_for_table(self.widget(index))
        return None

    def _tabbar_right_clicked(self, index: int):
        if index < 0:  # Clicked on the empty space
            return
        else:  # Clicked on an existing tab
            menu = QtW.QMenu(self)
            rename_action = menu.addAction("Rename Tab")
            delete_action = menu.addAction("Delete Tab")
            action = menu.exec_(QtGui.QCursor.pos())
            if action == rename_action:
                self._line_edit.start_edit(index)
            elif action == delete_action:
                self.removeTab(index)

    def _add_new_tab(self):
        table = QSpreadsheet()
        table.update_model(WidgetDataModel(value=None, type=StandardType.TABLE))
        table.setHeaderFormat(QSpreadsheet.HeaderFormat.Alphabetic)
        self.addTab(table, f"Sheet-{self.count() + 1}")
        self.setCurrentIndex(self.count() - 1)
        self._control.update_for_table(table)
        return None

    @protocol_override
    def update_model(self, model: WidgetDataModel):
        if not isinstance(value := model.value, Mapping):
            raise ValueError(f"Expected a dict, got {type(value)}")
        self.clear()
        for sheet_name, each in value.items():
            table = QSpreadsheet()
            table.update_model(WidgetDataModel(value=each, type=StandardType.TABLE))
            table.setHeaderFormat(QSpreadsheet.HeaderFormat.Alphabetic)
            self.addTab(table, str(sheet_name))
        if self.count() > 0:
            self.setCurrentIndex(0)
            self._control.update_for_table(self.widget(0))
        self._model_type = model.type
        return None

    @protocol_override
    def to_model(self) -> WidgetDataModel[dict[str, np.ndarray]]:
        index = self.currentIndex()
        table_meta = self.widget(index)._prep_table_meta()
        return WidgetDataModel(
            value={
                self.tabText(i): self.widget(i).to_model().value
                for i in range(self.count())
            },
            type=self.model_type(),
            extension_default=".xlsx",
            metadata=ExcelMeta(
                current_position=table_meta.current_position,
                selections=table_meta.selections,
                current_sheet=self.tabText(index),
            ),
        )

    @protocol_override
    def control_widget(self) -> QExcelTableStackControl:
        return self._control

    @protocol_override
    def model_type(self):
        return self._model_type

    @protocol_override
    def is_modified(self) -> bool:
        return any(self.widget(i).is_modified() for i in range(self.count()))

    @protocol_override
    def set_modified(self, value: bool) -> None:
        for i in range(self.count()):
            self.widget(i).set_modified(value)

    @protocol_override
    def size_hint(self) -> tuple[int, int]:
        return 400, 300

    @protocol_override
    def is_editable(self) -> bool:
        return self._edit_trigger == _EDIT_ENABLED

    @protocol_override
    def set_editable(self, value: bool) -> None:
        self._edit_trigger = _EDIT_ENABLED if value else _EDIT_DISABLED
        for i in range(self.count()):
            self.widget(i).set_editable(value)

    @protocol_override
    def mergeable_model_types(self) -> list[str]:
        return [StandardType.EXCEL, StandardType.TABLE]

    @protocol_override
    def merge_model(self, model: WidgetDataModel) -> None:
        if model.type == StandardType.EXCEL:
            assert isinstance(model.value, dict)
            for key, value in model.value.items():
                table = QSpreadsheet()
                table.setHeaderFormat(QSpreadsheet.HeaderFormat.Alphabetic)
                table.update_model(
                    WidgetDataModel(value=value, type=StandardType.TABLE)
                )
                self.addTab(table, key)
        elif model.type == StandardType.TABLE:
            table = QSpreadsheet()
            table.setHeaderFormat(QSpreadsheet.HeaderFormat.Alphabetic)
            table.update_model(model)
            self.addTab(table, model.title)
        else:
            raise ValueError(f"Cannot merge {model.type} with {StandardType.EXCEL}")

    if TYPE_CHECKING:

        def widget(self, index: int) -> QSpreadsheet: ...
        def tabBar(self) -> QRightClickableTabBar: ...


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

    def update_for_table(self, table: QSpreadsheet):
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
