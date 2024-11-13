from __future__ import annotations

from abc import ABC, abstractmethod
import sys
import logging
from typing import TYPE_CHECKING, Any, Callable, NamedTuple

from qtpy import QtGui, QtCore
from qtpy.QtCore import Qt
from himena.consts import StandardTypes
from himena.types import WidgetDataModel
from himena.model_meta import TableMeta
from himena.builtins.qt.widgets._table_base import QTableBase

if TYPE_CHECKING:
    from typing import TypeGuard
    import pandas as pd
    import polars as pl

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
            text = _DEFAULT_FORMATTERS.get(dtype.kind, str)(value)
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


def _format_float(value, ndigits: int = 4) -> str:
    """convert string to int or float if possible"""
    if value is None:
        return "null"
    if 0.1 <= abs(value) < 10 ** (ndigits + 1) or value == 0:
        text = f"{value:.{ndigits}f}"
    else:
        text = f"{value:.{ndigits-1}e}"

    return text


def _format_int(value, ndigits: int = 4) -> str:
    if value is None:
        return "null"
    if 0.1 <= abs(value) < 10 ** (ndigits + 1) or value == 0:
        text = str(value)
    else:
        text = f"{value:.{ndigits-1}e}"

    return text


def _format_datetime(value):
    return str(value)


_DEFAULT_FORMATTERS: dict[int, Callable[[Any], str]] = {
    "i": _format_int,
    "u": _format_int,
    "f": _format_float,
    "t": _format_datetime,
}


class QDataFrameView(QTableBase):
    """A table widget for viewing any dataframe that implements `__dataframe__()`"""

    def update_model(self, model: WidgetDataModel):
        df = model.value
        if is_pandas_dataframe(df):
            self.setModel(QDataFrameModel(PandasWrapper(df)))
        elif is_polars_dataframe(df):
            self.setModel(QDataFrameModel(PolarsWrapper(df)))
        else:
            raise ValueError(f"Unsupported dataframe type: {type(df)}")
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
        return None

    def to_model(self) -> WidgetDataModel[list[list[Any]]]:
        return WidgetDataModel(
            value=self.model().df.unwrap(),
            type=self.model_type(),
            extension_default=".csv",
            additional_data=self._prep_table_meta(),
        )

    def model_type(self) -> str:
        return StandardTypes.DATAFRAME

    def is_modified(self) -> bool:
        return False

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
        csv_text = self.model().df.to_csv_string(r0, r1, c0, c1)
        clipboard = QtGui.QGuiApplication.clipboard()
        clipboard.setText(csv_text)

    if TYPE_CHECKING:

        def model(self) -> QDataFrameModel: ...


def is_pandas_dataframe(df) -> TypeGuard[pd.DataFrame]:
    typ = type(df)
    if (
        typ.__name__ != "DataFrame"
        or "pandas" not in sys.modules
        or typ.__module__.split(".")[0] != "pandas"
    ):
        return False
    import pandas as pd

    return isinstance(df, pd.DataFrame)


def is_polars_dataframe(df) -> TypeGuard[pl.DataFrame]:
    typ = type(df)
    if (
        typ.__name__ != "DataFrame"
        or "polars" not in sys.modules
        or typ.__module__.split(".")[0] != "polars"
    ):
        return False
    import polars as pl

    return isinstance(df, pl.DataFrame)


class DataFrameWrapper(ABC):
    def __init__(self, df):
        self._df = df

    def unwrap(self):
        return self._df

    @abstractmethod
    def __getitem__(self, key: tuple[int, int]) -> Any:
        raise NotImplementedError

    @abstractmethod
    def num_rows(self) -> int:
        raise NotImplementedError

    @abstractmethod
    def num_columns(self) -> int:
        raise NotImplementedError

    @abstractmethod
    def column_names(self) -> list[str]:
        raise NotImplementedError

    @abstractmethod
    def get_dtype(self, index: int) -> DtypeTuple:
        raise NotImplementedError

    @abstractmethod
    def to_csv_string(self, r0: int, r1: int, c0: int, c1: int) -> str:
        raise NotImplementedError


class PandasWrapper(DataFrameWrapper):
    def __init__(self, df: pd.DataFrame):
        self._df = df

    def __getitem__(self, key: tuple[int, int]) -> Any:
        return self._df.iloc[key]

    def num_rows(self) -> int:
        return self._df.shape[0]

    def num_columns(self) -> int:
        return self._df.shape[1]

    def column_names(self) -> list[str]:
        return self._df.columns.tolist()

    def get_dtype(self, index: int) -> DtypeTuple:
        import numpy as np

        pd_dtype = self._df.dtypes.iloc[index]
        if isinstance(pd_dtype, np.dtype):
            return DtypeTuple(pd_dtype.name, pd_dtype.kind)
        return DtypeTuple(str(pd_dtype), getattr(pd_dtype, "kind", "O"))

    def to_csv_string(self, r0: int, r1: int, c0: int, c1: int) -> str:
        return self._df.iloc[r0:r1, c0:c1].to_csv(sep="\t")


class PolarsWrapper(DataFrameWrapper):
    def __init__(self, df: pl.DataFrame):
        self._df = df

    def __getitem__(self, key: tuple[int, int]) -> Any:
        return self._df[key]

    def num_rows(self) -> int:
        return self._df.shape[0]

    def num_columns(self) -> int:
        return self._df.shape[1]

    def column_names(self) -> list[str]:
        return self._df.columns

    def get_dtype(self, index: int) -> DtypeTuple:
        import polars as pl

        pl_dtype = self._df.dtypes[index]
        if pl_dtype == pl.Int8:
            return DtypeTuple("Int8", "i")
        if pl_dtype == pl.Int16:
            return DtypeTuple("Int16", "i")
        if pl_dtype == pl.Int32:
            return DtypeTuple("Int32", "i")
        if pl_dtype == pl.Int64:
            return DtypeTuple("Int64", "i")
        if pl_dtype == pl.UInt8:
            return DtypeTuple("UInt8", "u")
        if pl_dtype == pl.UInt16:
            return DtypeTuple("UInt16", "u")
        if pl_dtype == pl.UInt32:
            return DtypeTuple("UInt32", "u")
        if pl_dtype == pl.UInt64:
            return DtypeTuple("UInt64", "u")
        if pl_dtype == pl.Float32:
            return DtypeTuple("Float32", "f")
        if pl_dtype == pl.Float64:
            return DtypeTuple("Float64", "f")
        if pl_dtype == pl.Boolean:
            return DtypeTuple("Boolean", "b")
        return DtypeTuple(str(pl_dtype), "O")

    def to_csv_string(self, r0: int, r1: int, c0: int, c1: int) -> str:
        return self._df[r0:r1, c0:c1].write_csv(separator="\t")


class DtypeTuple(NamedTuple):
    name: str
    kind: str
