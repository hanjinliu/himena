from __future__ import annotations
from typing import Any

from qtpy import QtCore, QtWidgets as QtW, QtGui
from himena.types import WidgetDataModel
from himena.consts import StandardType
from himena.standards.model_meta import ListMeta
from himena.workflow import ProgrammaticMethod
from himena.qt._utils import get_main_window
from dataclasses import asdict, is_dataclass


class QResultStack(QtW.QTableWidget):
    """A special widget for displaying measurement results."""

    __himena_widget_id__ = "QResultStack"

    def __init__(self, parent: QtW.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAlternatingRowColors(True)
        self.setSelectionMode(QtW.QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setSelectionBehavior(QtW.QAbstractItemView.SelectionBehavior.SelectRows)
        self.setVerticalScrollMode(QtW.QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.setHorizontalScrollMode(QtW.QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.horizontalHeader().hide()
        self.horizontalHeader().setDefaultSectionSize(56)
        self._items: list[dict[str, Any]] = []  # the actual python objects
        self._roi_height = 40  # default row height

    def append_result(self, item: dict[str, Any]) -> None:
        """Append a new result to the stack."""
        # coerce item to a dict-like object
        if isinstance(item, dict):
            pass
        elif is_dataclass(item):
            item = asdict(item)
        else:
            item = dict(item)
        self.insertRow(self.rowCount())
        self.setRowHeight(self.rowCount(), self._roi_height)
        add_new_column = len(item) > self.columnCount()
        if add_new_column:
            self.setColumnCount(len(item))
        flags = QtCore.Qt.ItemFlag.ItemIsEnabled | QtCore.Qt.ItemFlag.ItemIsSelectable
        for column, (key, value) in enumerate(item.items()):
            label = QtW.QLabel(
                f"<b><font color='#808080' style='font-size:8px'>{key}:</font></b><br>{value!r}"
            )
            label.setContentsMargins(4, 0, 4, 1)
            label.setAlignment(
                QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignTop
            )
            table_item = QtW.QTableWidgetItem()
            table_item.setToolTip(f"{key}: {value!r}")
            table_item.setFlags(flags)
            model_index = self.model().index(self.rowCount() - 1, column)
            self.setIndexWidget(model_index, label)
            self.setItem(self.rowCount() - 1, column, table_item)
        self._items.append(item)

    def update_model(self, model: WidgetDataModel) -> None:
        """Update the model with new data."""
        vals = model.value
        if not hasattr(vals, "__iter__"):
            raise TypeError(f"Expected an iterable, got {type(vals)}")
        self.clear()
        for val in vals:
            self.append_result(val)

    def to_model(self) -> WidgetDataModel:
        return WidgetDataModel(
            value=self._items,
            type=StandardType.RESULTS,
            title="Results",
            metadata=ListMeta(selections=self.selections()),
            workflow=ProgrammaticMethod().construct_workflow(),
        )

    def model_type(self) -> StandardType:
        return StandardType.RESULTS

    def size_hint(self) -> tuple[int, int]:
        """Return the size hint for the widget."""
        return 320, 320

    def selections(self) -> list[int]:
        """Return the selected row indices."""
        return sorted({i.row() for i in self.selectedIndexes()})

    def _make_context_menu(self) -> QtW.QMenu:
        menu = QtW.QMenu(self)
        menu.setToolTipsVisible(True)
        copy_action = menu.addAction(
            "Copy", lambda: self._copy_items(self.selections())
        )
        copy_action.setToolTip("Copy selected items to clipboard")
        select_action = menu.addAction(
            "Select Rows With Same Keys", lambda: self._select_rows_with_same_keys()
        )
        select_action.setToolTip("Select all rows with the same keys")
        return menu

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        """Handle mouse press events."""
        if event.buttons() & QtCore.Qt.MouseButton.RightButton:
            menu = self._make_context_menu()
            self.selectRow(self.rowAt(event.y()))
            menu.exec(event.globalPos())
        else:
            super().mousePressEvent(event)

    def _copy_items(self, indices: list[int]) -> None:
        """Copy selected items to clipboard."""
        if not indices:
            return
        items = [self._items[i] for i in indices]
        ui = get_main_window(self)
        model = WidgetDataModel(value=items, type=StandardType.RESULTS)
        ui.set_clipboard(text=repr(items), internal_data=model)

    def _select_rows_with_same_keys(self) -> None:
        """Select rows with the same keys."""
        sels = self.selections()
        if not sels:
            return
        item_ref = self._items[sels[0]]
        self.clearSelection()
        selected = []
        for i, item in enumerate(self._items):
            if item.keys() == item_ref.keys():
                selected.append(i)
        for i in selected:
            for j in range(self.columnCount()):
                self.item(i, j).setSelected(True)

    def keyPressEvent(self, e):
        if (
            e.key() == QtCore.Qt.Key.Key_C
            and e.modifiers() & QtCore.Qt.KeyboardModifier.ControlModifier
        ):
            self._copy_items(self.selections())
            return
        return super().keyPressEvent(e)
