from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, NamedTuple

import numpy as np
from qtpy import QtGui, QtCore, QtWidgets as QtW
from qtpy.QtCore import Qt

from himena.consts import StandardType
from himena.types import WidgetDataModel
from himena.standards.model_meta import DataFrameMeta, TableMeta
from himena.standards import plotting as hplt
from himena_builtins.qt.widgets._table_components import (
    QTableBase,
    QSelectionRangeEdit,
    format_table_value,
)
from himena_builtins.qt.widgets._splitter import QSplitterHandle
from himena.plugins import validate_protocol
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

    __himena_widget_id__ = "builtins:QDataFrameView"
    __himena_display_name__ = "Built-in DataFrame Viewer"

    def __init__(self):
        super().__init__()
        self._control: QDataFrameViewControl | None = None
        self._model_type = StandardType.DATAFRAME

    @validate_protocol
    def update_model(self, model: WidgetDataModel):
        self.setModel(QDataFrameModel(wrap_dataframe(model.value)))

        if isinstance(meta := model.metadata, TableMeta):
            self._selection_model.clear()
            if (pos := meta.current_position) is not None:
                index = self.model().index(*pos)
                self.setCurrentIndex(index)
                self._selection_model.current_index = pos
            for (r0, r1), (c0, c1) in meta.selections:
                self._selection_model.append((slice(r0, r1), slice(c0, c1)))

        if self._control is None:
            self._control = QDataFrameViewControl(self)
        self._control.update_for_table(self)
        self._model_type = model.type
        self.update()
        return None

    @validate_protocol
    def to_model(self) -> WidgetDataModel[list[list[Any]]]:
        return WidgetDataModel(
            value=self.model().df.unwrap(),
            type=self.model_type(),
            extension_default=".csv",
            metadata=self._prep_table_meta(cls=DataFrameMeta),
        )

    @validate_protocol
    def model_type(self) -> str:
        return self._model_type

    @validate_protocol
    def is_modified(self) -> bool:
        return False

    @validate_protocol
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
        sels = self._selection_model.ranges
        if len(sels) > 1:
            _LOGGER.warning("Multiple selections.")
            return

        rsl, csl = sels[0]
        r0, r1 = rsl.start, rsl.stop
        c0, c1 = csl.start, csl.stop
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


class QDataFramePlotView(QtW.QSplitter):
    """A widget for viewing dataframe on the left and plot on the right."""

    __himena_widget_id__ = "builtins:QDataFramePlotView"
    __himena_display_name__ = "Built-in DataFrame Plot View"

    def __init__(self):
        from himena_builtins.qt.plot._canvas import QModelMatplotlibCanvas

        super().__init__(QtCore.Qt.Orientation.Horizontal)
        self._table_widget = QDataFrameView()
        self._table_widget.setSizePolicy(
            QtW.QSizePolicy.Policy.Expanding, QtW.QSizePolicy.Policy.Expanding
        )
        self._plot_widget = QModelMatplotlibCanvas()
        self._plot_widget.update_model(
            WidgetDataModel(value=hplt.figure(), type=StandardType.PLOT)
        )
        right = QtW.QWidget()
        right.setSizePolicy(
            QtW.QSizePolicy.Policy.Expanding, QtW.QSizePolicy.Policy.Expanding
        )
        layout_right = QtW.QVBoxLayout(right)
        layout_right.setContentsMargins(0, 0, 0, 0)
        layout_right.setSpacing(1)
        layout_right.addWidget(self._plot_widget._toolbar)
        layout_right.addWidget(self._plot_widget)
        self._model_type = StandardType.DATAFRAME_PLOT

        self.addWidget(self._table_widget)
        self.addWidget(right)
        self.setStretchFactor(0, 1)
        self.setStretchFactor(1, 2)

    def createHandle(self):
        return QSplitterHandle(self, side="left")

    @validate_protocol
    def update_model(self, model: WidgetDataModel):
        df = wrap_dataframe(model.value)
        col_names = df.column_names()
        if len(col_names) == 0:
            raise ValueError("No columns in the dataframe.")
        elif len(col_names) == 1:
            xlabel = "index"
            ylabel = col_names[0]
            x = np.arange(df.num_rows())
            y = df.column_to_array(ylabel)
        else:
            xlabel = col_names[0]
            ylabel = col_names[1]
            x = df.column_to_array(xlabel)
            y = df.column_to_array(ylabel)
        fig = hplt.figure()
        fig.axes.x.label = xlabel
        fig.axes.y.label = ylabel
        fig.plot(x, y)
        self._table_widget.update_model(model)
        self._plot_widget.update_model(
            WidgetDataModel(value=fig, type=StandardType.PLOT)
        )
        self._model_type = model.type
        return None

    @validate_protocol
    def to_model(self) -> WidgetDataModel:
        return self._table_widget.to_model()

    @validate_protocol
    def model_type(self) -> str:
        return self._model_type

    @validate_protocol
    def is_modified(self) -> bool:
        return self._table_widget.is_modified()

    @validate_protocol
    def control_widget(self):
        return self._table_widget.control_widget()

    @validate_protocol
    def size_hint(self):
        return 480, 300

    @validate_protocol
    def window_added_callback(self):
        # adjuct size
        self.setSizes([160, self.width() - 160])
        return None

    @validate_protocol
    def theme_changed_callback(self, theme):
        # self._table_widget.theme_changed_callback(theme)
        self._plot_widget.theme_changed_callback(theme)
