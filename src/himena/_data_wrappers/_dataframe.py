from __future__ import annotations

from abc import ABC, abstractmethod
import sys
from typing import TYPE_CHECKING, Any, NamedTuple

if TYPE_CHECKING:
    from typing import TypeGuard
    import pandas as pd
    import polars as pl


def _see_imported_module(arr: Any, module: str) -> bool:
    typ = type(arr)
    if (
        typ.__name__ != "DataFrame"
        or module not in sys.modules
        or typ.__module__.split(".")[0] != module
    ):
        return False
    return True


def is_pandas_dataframe(df) -> TypeGuard[pd.DataFrame]:
    if _see_imported_module(df, "pandas"):
        import pandas as pd

        return isinstance(df, pd.DataFrame)
    return False


def is_polars_dataframe(df) -> TypeGuard[pl.DataFrame]:
    if _see_imported_module(df, "polars"):
        import polars as pl

        return isinstance(df, pl.DataFrame)
    return False


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

    def type_name(self) -> str:
        mod = type(self._df).__module__.split(".")[0]
        return f"{mod}.{type(self._df).__name__}"


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
    """Normalized dtype description."""

    name: str
    kind: str


def wrap_dataframe(df) -> DataFrameWrapper:
    if is_pandas_dataframe(df):
        return PandasWrapper(df)
    if is_polars_dataframe(df):
        return PolarsWrapper(df)
    raise TypeError(f"Unsupported dataframe type: {type(df)}")
