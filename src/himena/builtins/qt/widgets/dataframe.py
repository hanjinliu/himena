from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, NamedTuple

from qtpy import QtGui, QtCore, QtWidgets as QtW
from qtpy.QtCore import Qt

from himena.consts import StandardType
from himena.types import WidgetDataModel
from himena.model_meta import DataFrameMeta, TableMeta
from himena.builtins.qt.widgets._table_base import (
    QTableBase,
    QSelectionRangeEdit,
    format_table_value,
)
from himena.plugins import protocol_override
from himena._data_wrappers import wrap_dataframe, DataFrameWrapper


_LOGGER = logging.getLogger(__name__)


class QDataFrameModel(QtCore.QAbstractTableModel):
    """Table model for data frame."""

    def __init__(self, df: DataFrameWrapper, parent=None):
        super().__init__(parent)
        self._df = df

    @property
    def df(self) -> DataFrameWrapper:
        return self._df

    def rowCount(self, parent=None):
        return self.df.num_rows()

    def columnCount(self, parent=None):
        return self.df.num_columns()

    def data(
        self,
        index: QtCore.QModelIndex,
        role: Qt.ItemDataRole = Qt.ItemDataRole.DisplayRole,
    ):
        if not index.isValid():
            return QtCore.QVariant()
        if role != Qt.ItemDataRole.DisplayRole:
            return QtCore.QVariant()
        r, c = index.row(), index.column()
        df = self.df
        if r < self.rowCount() and c < self.columnCount():
            value = df[r, c]
            dtype = df.get_dtype(c)
            text = format_table_value(value, dtype.kind)
            return text
        return QtCore.QVariant()

    def flags(self, index):
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ):
        if orientation == Qt.Orientation.Horizontal:
            if role == Qt.ItemDataRole.DisplayRole:
                if section >= self.df.num_columns():
                    return None
                return str(self.df.column_names()[section])
            elif role == Qt.ItemDataRole.ToolTipRole:
                if section < self.df.num_columns():
                    return self._column_tooltip(section)
                return None

        if orientation == Qt.Orientation.Vertical:
            if role == Qt.ItemDataRole.DisplayRole:
                return str(section)

    def _column_tooltip(self, section: int):
        name = self.df.column_names()[section]
        dtype = self.df.get_dtype(section)
        return f"{name} (dtype: {dtype.name})"


class QDataFrameView(QTableBase):
    """A table widget for viewing dataframe."""

    def __init__(self):
        super().__init__()
        self._control: QDataFrameViewControl | None = None

    @protocol_override
    def update_model(self, model: WidgetDataModel):
        self.setModel(QDataFrameModel(wrap_dataframe(model.value)))
        self.setSelectionModel(QtCore.QItemSelectionModel(self.model()))

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

        if self._control is None:
            self._control = QDataFrameViewControl(self)
        self._control.update_for_table(self)
        self.update()
        return None

    @protocol_override
    def to_model(self) -> WidgetDataModel[list[list[Any]]]:
        return WidgetDataModel(
            value=self.model().df.unwrap(),
            type=self.model_type(),
            extension_default=".csv",
            additional_data=self._prep_table_meta(cls=DataFrameMeta),
        )

    @protocol_override
    def model_type(self) -> str:
        return StandardType.DATAFRAME

    @protocol_override
    def is_modified(self) -> bool:
        return False

    @protocol_override
    def control_widget(self):
        return self._control

    def keyPressEvent(self, e: QtGui.QKeyEvent) -> None:
        if e.matches(QtGui.QKeySequence.StandardKey.Copy):
            return self.copy_data()
        if (
            e.modifiers() & Qt.KeyboardModifier.ControlModifier
            and e.key() == QtCore.Qt.Key.Key_F
        ):
            self._find_string()
            return
        return super().keyPressEvent(e)

    def copy_data(self):
        model = self.selectionModel()
        if not model.hasSelection():
            return
        qselections = self.selectionModel().selection()
        if len(qselections) > 1:
            _LOGGER.warning("Multiple selections.")
            return

        qsel = next(iter(qselections))
        r0, r1 = qsel.left(), qsel.right() + 1
        c0, c1 = qsel.top(), qsel.bottom() + 1
        csv_text = self.model().df.get_subset(r0, r1, c0, c1).to_csv_string("\t")
        clipboard = QtGui.QGuiApplication.clipboard()
        clipboard.setText(csv_text)

    if TYPE_CHECKING:

        def model(self) -> QDataFrameModel: ...


_R_CENTER = QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter


class QDataFrameViewControl(QtW.QWidget):
    def __init__(self, table: QDataFrameView):
        super().__init__()
        layout = QtW.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(_R_CENTER)
        self._label = QtW.QLabel("")
        self._label.setAlignment(_R_CENTER)
        layout.addWidget(self._label)
        layout.addWidget(QSelectionRangeEdit(table))

    def update_for_table(self, table: QDataFrameView):
        model = table.model()
        self._label.setText(
            f"{model.df.type_name()} ({model.rowCount()}, {model.columnCount()})"
        )
        return None


class DtypeTuple(NamedTuple):
    """Normalized dtype description."""

    name: str
    kind: str
