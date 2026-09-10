from __future__ import annotations

import re
from typing import TYPE_CHECKING, Iterator

from qtpy import QtWidgets as QtW, QtGui, QtCore
from qtpy.QtCore import Qt

from himena.consts import MonospaceFontFamily
from himena.profile import WarningFilter
from himena.qt.settings._shared import QInstruction

if TYPE_CHECKING:
    from himena.widgets import MainWindow


class H:
    CATEGORY = 0
    MESSAGE = 1
    MODULE = 2


# Categories that are likely to be used. The combo box is editable so that any other
# category can be typed in.
COMMON_CATEGORIES = [
    "",
    "Warning",
    "UserWarning",
    "DeprecationWarning",
    "PendingDeprecationWarning",
    "FutureWarning",
    "RuntimeWarning",
    "SyntaxWarning",
    "ImportWarning",
    "ResourceWarning",
    "EncodingWarning",
]


class QWarningFilterPanel(QtW.QWidget):
    """Widget to edit the warning filters of the current profile."""

    def __init__(self, ui: MainWindow):
        super().__init__()
        self._ui = ui
        self._instruction = QInstruction(
            "Warnings listed here are not shown as a notification popup<br>"
            "(they are still sent to the standard error).<br>"
        )
        self._table = QWarningFilterTable(self)
        self._table.set_filters(self._ui.app_profile.warning_filters)

        self._add_button = QtW.QPushButton("Add", self)
        self._add_button.setToolTip("Add a new warning filter.")
        self._remove_button = QtW.QPushButton("Remove", self)
        self._remove_button.setToolTip("Remove the selected warning filters.")
        self._apply_button = QtW.QPushButton("Apply", self)
        self._apply_button.setMinimumWidth(160)
        self._msg_label = QtW.QLabel(self)
        self._msg_label.setMaximumWidth(280)

        self._footer = QtW.QWidget(self)
        _footer_layout = QtW.QHBoxLayout(self._footer)
        _footer_layout.setContentsMargins(0, 0, 0, 0)
        _footer_layout.addWidget(self._add_button)
        _footer_layout.addWidget(self._remove_button)
        _footer_layout.addStretch()
        _footer_layout.addWidget(self._msg_label)
        _footer_layout.addWidget(self._apply_button)

        layout = QtW.QVBoxLayout(self)
        layout.addWidget(self._instruction)
        layout.addWidget(self._table)
        layout.addWidget(self._footer)

        self._add_button.clicked.connect(self._add_filter)
        self._remove_button.clicked.connect(self._remove_selected_filters)
        self._apply_button.clicked.connect(self._apply_changes)
        self._table.changed.connect(self._on_table_changed)
        self._apply_button.setEnabled(False)

    def _add_filter(self):
        self._table.append_filter(WarningFilter())
        self._table.setCurrentCell(self._table.rowCount() - 1, H.CATEGORY)

    def _remove_selected_filters(self):
        rows = sorted(
            {index.row() for index in self._table.selectedIndexes()}, reverse=True
        )
        for row in rows:
            self._table.removeRow(row)
        if rows:
            self._on_table_changed()

    def _apply_changes(self):
        filters = list(self._table.iter_filters())
        if _invalid_patterns(filters):
            self._set_message("Invalid regular expression")
        else:
            self._ui.app_profile.with_warning_filters(filters).save()
            self._set_message("Changes applied.")
            self._apply_button.setEnabled(False)
            self._add_button.setFocus()

    def _on_table_changed(self):
        self._msg_label.clear()
        self._apply_button.setEnabled(True)

    def _set_message(self, text: str, sec: float = 3.0):
        """Show message for the specified number of seconds."""
        self._msg_label.setText(text)
        QtCore.QTimer.singleShot(int(sec * 1000), self._msg_label.clear)


class QWarningFilterTable(QtW.QTableWidget):
    """Table that lists the warning filters."""

    changed = QtCore.Signal()

    def __init__(self, parent: QtW.QWidget | None = None):
        super().__init__(parent)
        self.setColumnCount(3)
        self.setHorizontalHeaderLabels(["Category", "Message", "Module"])
        self.setSelectionBehavior(QtW.QAbstractItemView.SelectionBehavior.SelectRows)
        self.setShowGrid(False)
        self.verticalHeader().setVisible(False)
        self.verticalHeader().setDefaultSectionSize(22)
        self.horizontalHeader().setStretchLastSection(True)
        self.setColumnWidth(H.CATEGORY, 170)
        self.setColumnWidth(H.MESSAGE, 180)
        self.setFont(QtGui.QFont(MonospaceFontFamily))
        self.itemChanged.connect(lambda *_: self.changed.emit())

    def set_filters(self, filters: list[WarningFilter]) -> None:
        """Update the table contents with the given filters."""
        with QtCore.QSignalBlocker(self):
            self.setRowCount(0)
            for filt in filters:
                self._insert_filter(filt)

    def append_filter(self, filt: WarningFilter) -> None:
        """Append a filter as the last row."""
        self._insert_filter(filt)
        self.changed.emit()

    def iter_filters(self) -> Iterator[WarningFilter]:
        """Iterate over the filters defined in this table."""
        for row in range(self.rowCount()):
            yield WarningFilter(
                action="ignore",
                category=self._category_combo(row).currentText().strip(),
                message=self._text_at(row, H.MESSAGE),
                module=self._text_at(row, H.MODULE),
            )

    def _insert_filter(self, filt: WarningFilter) -> None:
        row = self.rowCount()
        self.insertRow(row)

        category_combo = QtW.QComboBox()
        category_combo.setEditable(True)
        category_combo.addItems(COMMON_CATEGORIES)
        category_combo.setCurrentText(filt.category)
        category_combo.lineEdit().setPlaceholderText("Any category")
        category_combo.setToolTip(
            "Name of the warning category, such as 'DeprecationWarning'. Subclasses "
            "of the category also match."
        )
        category_combo.currentTextChanged.connect(lambda *_: self.changed.emit())
        self.setCellWidget(row, H.CATEGORY, category_combo)

        item_message = QtW.QTableWidgetItem(filt.message)
        item_message.setToolTip("Regular expression searched in the warning message.")
        self.setItem(row, H.MESSAGE, item_message)

        item_module = QtW.QTableWidgetItem(filt.module)
        item_module.setToolTip(
            "Regular expression searched in the path of the file that raised the "
            "warning, such as 'skimage'."
        )
        self.setItem(row, H.MODULE, item_module)
        return None

    def _category_combo(self, row: int) -> QtW.QComboBox:
        return self.cellWidget(row, H.CATEGORY)

    def _text_at(self, row: int, column: int) -> str:
        if item := self.item(row, column):
            return item.text().strip()
        return ""

    def keyPressEvent(self, e: QtGui.QKeyEvent) -> None:
        if e.key() == Qt.Key.Key_Delete and self.state() != self.State.EditingState:
            for item in self.selectedItems():
                item.setText("")
            return None
        return super().keyPressEvent(e)


def _invalid_patterns(filters: list[WarningFilter]) -> list[str]:
    """Return the patterns that are not valid regular expressions."""
    invalid: list[str] = []
    for filt in filters:
        for pattern in [filt.message, filt.module]:
            if not pattern:
                continue
            try:
                re.compile(pattern)
            except re.error:
                invalid.append(pattern)
    return invalid
