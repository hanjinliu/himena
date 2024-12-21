from __future__ import annotations

from abc import ABC, abstractmethod
import csv
import importlib
import importlib.metadata
import importlib.resources
import io
from pathlib import Path
import sys
from typing import TYPE_CHECKING, Any, Mapping, NamedTuple
import numpy as np
from himena.consts import ExcelFileTypes
from himena._utils import lru_cache

if TYPE_CHECKING:
    from typing import TypeGuard, Self
    import pandas as pd
    import polars as pl
    import pyarrow as pa
    import narwhals as nw


@lru_cache(maxsize=1)
def list_installed_dataframe_packages() -> list[str]:
    """Return a list of installed dataframe package names."""
    installed: list[str] = ["dict"]
    for entry in importlib.metadata.distributions():
        if entry.name in {"pandas", "polars", "pyarrow"}:
            installed.append(entry.name)
    return installed


def read_csv(mod: str, file) -> Any:
    if mod == "dict":
        csv_reader = csv.reader(file)
        header = next(csv_reader)
        data = {k: [] for k in header}
        for row in csv_reader:
            for k, v in zip(header, row):
                data[k].append(v)
        return {k: np.array(v) for k, v in data.items()}
    if mod == "pandas":
        return importlib.import_module(mod).read_csv(file, header=0)
    elif mod == "polars":
        return importlib.import_module(mod).read_csv(file, has_header=True)
    elif mod == "pyarrow":
        if isinstance(file, io.StringIO):
            # pyarrow does not support StringIO
            file = io.BytesIO(file.getvalue().encode())
        return importlib.import_module(mod + ".csv").read_csv(file)
    else:
        raise ValueError(f"Unsupported module: {mod}")


def _see_imported_module(arr: Any, module: str, class_name: str = "DataFrame") -> bool:
    typ = type(arr)
    if (
        typ.__name__ != class_name
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


def is_pyarrow_table(df) -> TypeGuard[pa.Table]:
    if _see_imported_module(df, "pyarrow", "Table"):
        import pyarrow as pa

        return isinstance(df, pa.Table)
    return False


def is_narwhals_dataframe(df) -> TypeGuard[nw.DataFrame]:
    if _see_imported_module(df, "narwhals"):
        import narwhals as nw

        nw.from_native
        return isinstance(df, nw.DataFrame)
    return False


class DataFrameWrapper(ABC):
    def __init__(self, df):
        self._df = df

    def unwrap(self):
        return self._df

    def __repr__(self) -> str:
        return f"{self.type_name()} {self.shape} of data:\n{self._df!r}"

    @abstractmethod
    def __getitem__(self, key: tuple[int, int]) -> Any:
        """Return the value at the given row and column indices"""

    @abstractmethod
    def get_subset(self, r0, r1, c0, c1) -> DataFrameWrapper:
        """Return a subset of the dataframe by slicing at df[r0:r1, c0, c1]."""

    @abstractmethod
    def num_rows(self) -> int:
        """Return the number of rows in the dataframe."""

    @abstractmethod
    def num_columns(self) -> int:
        """Return the number of columns in the dataframe."""

    @abstractmethod
    def column_names(self) -> list[str]:
        """Return the names of the columns in the dataframe."""

    @abstractmethod
    def get_dtype(self, index: int) -> DtypeTuple:
        """Return the dtype of the column at the given index."""

    @classmethod
    @abstractmethod
    def from_csv_string(self, str_or_buf: str | io.StringIO, separator: str) -> Self:
        """Create a dataframe from a CSV string."""

    @abstractmethod
    def to_csv_string(self, separator: str) -> str:
        """Convert the dataframe to a CSV string."""

    @abstractmethod
    def to_list(self) -> list[list[Any]]:
        """Convert dataframe to a 2D list"""

    @abstractmethod
    def column_to_array(self, name: str) -> np.ndarray:
        """Return a column of the dataframe as an 1D numpy array."""

    @classmethod
    @abstractmethod
    def from_dict(cls, data: dict[str, np.ndarray]) -> DataFrameWrapper:
        """Create a dataframe from a dictionary of column names and arrays."""

    def to_dict(self) -> dict[str, np.ndarray]:
        return {k: self.column_to_array(k) for k in self.column_names()}

    def type_name(self) -> str:
        mod = type(self._df).__module__.split(".")[0]
        return f"{mod}.{type(self._df).__name__}"

    @property
    def dtypes(self) -> list[DtypeTuple]:
        return [self.get_dtype(i) for i in range(self.num_columns())]

    @property
    def shape(self) -> tuple[int, int]:
        return self.num_rows(), self.num_columns()

    @abstractmethod
    def write(self, file: str | Path):
        """Write the dataframe to a file."""


class DictWrapper(DataFrameWrapper):
    def __init__(self, df: Mapping[str, np.ndarray]):
        self._df = df
        self._columns = list(df.keys())

    def __getitem__(self, key: tuple[int, int]) -> Any:
        r, c = key
        col_name = self._columns[c]
        return self._df[col_name][r]

    def get_subset(self, r0, r1, c0, c1) -> DictWrapper:
        keys = self._columns[c0:c1]
        return DictWrapper({k: self._df[k][r0:r1] for k in keys})

    def num_rows(self) -> int:
        return len(next(iter(self._df.values()), []))

    def num_columns(self) -> int:
        return len(self._columns)

    def column_names(self) -> list[str]:
        return self._columns

    def get_dtype(self, index: int) -> DtypeTuple:
        col_name = self._columns[index]
        dtype = self._df[col_name].dtype
        return DtypeTuple(str(dtype), dtype.kind)

    @classmethod
    def from_csv_string(self, str_or_buf: str | io.StringIO, separator: str):
        if isinstance(str_or_buf, str):
            buf = io.StringIO(str_or_buf)
        else:
            buf = str_or_buf
        csv_reader = csv.reader(buf, delimiter=separator)
        header = next(csv_reader)
        data = {k: [] for k in header}
        for row in csv_reader:
            for k, v in zip(header, row):
                data[k].append(v)
        return {k: np.array(v) for k, v in data.items()}

    def to_csv_string(self, separator: str) -> str:
        lines: list[str] = []
        for i in range(self.num_rows()):
            lines.append(
                separator.join(str(self._df[k][i]) for k in self.column_names())
            )
        return "\n".join(lines)

    def to_list(self) -> list[list[Any]]:
        return [
            [self._df[k][i] for k in self.column_names()]
            for i in range(self.num_rows())
        ]

    def column_to_array(self, name: str) -> np.ndarray:
        return np.asarray(self._df[name])

    @classmethod
    def from_dict(cls, data: dict) -> DataFrameWrapper:
        content: dict[str, np.ndarray] = {}
        length = -1
        for k, v in data.items():
            v_arr = np.asarray(v)
            if v_arr.ndim == 1:
                if length < 0:
                    length = len(v_arr)
                elif length != v_arr.size:
                    raise ValueError(
                        "All arrays must have the same length. Consensus length is "
                        f"{length} but got {v_arr.size} for {k!r}."
                    )
            elif v_arr.ndim > 1:
                raise ValueError("Only 1D arrays are supported.")
            content[k] = v_arr
        if length < 0:  # all arrays are scalar. Interpret as a single-row data frame.
            length = 1
        for k, v in content.items():
            if v.ndim == 0:
                content[k] = np.full(length, v)
        return DictWrapper(content)

    def write(self, file: str | Path):
        path = Path(file)
        with open(path, "w") as f:
            f.write(self.to_csv_string(","))


class PandasWrapper(DataFrameWrapper):
    def __init__(self, df: pd.DataFrame):
        self._df = df

    def __getitem__(self, key: tuple[int, int]) -> Any:
        return self._df.iloc[key]

    def get_subset(self, r0, r1, c0, c1) -> PandasWrapper:
        return PandasWrapper(self._df.iloc[r0:r1, c0:c1])

    def num_rows(self) -> int:
        return self._df.shape[0]

    def num_columns(self) -> int:
        return self._df.shape[1]

    def column_names(self) -> list[str]:
        return self._df.columns.tolist()

    def get_dtype(self, index: int) -> DtypeTuple:
        pd_dtype = self._df.dtypes.iloc[index]
        if isinstance(pd_dtype, np.dtype):
            return DtypeTuple(pd_dtype.name, pd_dtype.kind)
        return DtypeTuple(str(pd_dtype), getattr(pd_dtype, "kind", "O"))

    @classmethod
    def from_csv_string(
        cls, str_or_buf: str | io.StringIO, separator: str
    ) -> DataFrameWrapper:
        import pandas as pd

        if isinstance(str_or_buf, str):
            str_or_buf = io.StringIO(str_or_buf)
        return PandasWrapper(pd.read_csv(str_or_buf, sep=separator))

    def to_csv_string(self, separator: str) -> str:
        return self._df.to_csv(sep=separator, index=False)

    def to_list(self) -> list[list[Any]]:
        return self._df.values.tolist()

    def column_to_array(self, name: str) -> np.ndarray:
        return self._df[name].to_numpy()

    @classmethod
    def from_dict(cls, data: dict) -> DataFrameWrapper:
        import pandas as pd

        return PandasWrapper(pd.DataFrame(data))

    def write(self, file: str | Path):
        path = Path(file)
        if path.suffix == ".tsv":
            self._df.to_csv(path, sep="\t")
        elif path.suffix == ".parquet":
            self._df.to_parquet(path)
        elif path.suffix == ".feather":
            self._df.to_feather(path)
        elif path.suffix == ".json":
            self._df.to_json(path)
        elif path.suffix in (".html", ".htm"):
            self._df.to_html(path)
        elif path.suffix in ExcelFileTypes:
            self._df.to_excel(path)
        elif path.suffix == ".pickle":
            self._df.to_pickle(path)
        elif path.suffix == ".md":
            self._df.to_markdown(path)
        elif path.suffix in (".csv", ".txt"):
            self._df.to_csv(path)
        else:
            raise ValueError(
                "Cannot write a pandas dataframe to a file with the given extension "
                f"{path.suffix!r}"
            )


class PolarsWrapper(DataFrameWrapper):
    def __init__(self, df: pl.DataFrame):
        self._df = df

    def __getitem__(self, key: tuple[int, int]) -> Any:
        return self._df[key]

    def get_subset(self, r0, r1, c0, c1) -> PolarsWrapper:
        return PolarsWrapper(self._df[r0:r1, c0:c1])

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

    @classmethod
    def from_csv_string(
        cls, str_or_buf: str | io.StringIO, separator: str
    ) -> PolarsWrapper:
        import polars as pl

        if isinstance(str_or_buf, str):
            str_or_buf = io.StringIO(str_or_buf)
        return PolarsWrapper(pl.read_csv(str_or_buf, sep=separator))

    def to_csv_string(self, separator: str) -> str:
        return self._df.write_csv(separator=separator)

    def to_list(self) -> list[list[Any]]:
        return [list(row) for row in self._df.iter_rows()]

    def column_to_array(self, name: str) -> np.ndarray:
        return self._df[name].to_numpy()

    @classmethod
    def from_dict(cls, data: dict) -> DataFrameWrapper:
        import polars as pl

        return PolarsWrapper(pl.DataFrame(data))

    def write(self, file: str | Path):
        path = Path(file)
        if path.suffix == ".tsv":
            self._df.write_csv(path, separator="\t")
        elif path.suffix in (".csv", ".txt"):
            self._df.write_csv(path)
        elif path.suffix == ".parquet":
            self._df.write_parquet(path)
        elif path.suffix == ".json":
            self._df.write_json(path)
        elif path.suffix in ExcelFileTypes:
            self._df.write_excel(path)
        else:
            raise ValueError(
                "Cannot write a pandas dataframe to a file with the given extension "
                f"{path.suffix!r}"
            )


class PyarrowWrapper(DataFrameWrapper):
    def __init__(self, df: pa.Table):
        self._df = df

    def __getitem__(self, key: tuple[int, int]) -> Any:
        r, c = key
        col_name = self._df.column_names[c]
        return self._df[col_name][r].as_py()

    def get_subset(self, r0, r1, c0, c1) -> PyarrowWrapper:
        df_sub = self._df.slice(r0, r1 - r0).select(self._df.column_names[c0:c1])
        return PyarrowWrapper(df_sub)

    def num_rows(self) -> int:
        return self._df.num_rows

    def num_columns(self) -> int:
        return self._df.num_columns

    def column_names(self) -> list[str]:
        return self._df.column_names

    def get_dtype(self, index: int) -> DtypeTuple:
        import pyarrow as pa

        pa_type = self._df.schema[index]
        if pa_type == pa.int8():
            return DtypeTuple("int8", "i")
        if pa_type == pa.int16():
            return DtypeTuple("int16", "i")
        if pa_type == pa.int32():
            return DtypeTuple("int32", "i")
        if pa_type == pa.int64():
            return DtypeTuple("int64", "i")
        if pa_type == pa.uint8():
            return DtypeTuple("uint8", "u")
        if pa_type == pa.uint16():
            return DtypeTuple("uint16", "u")
        if pa_type == pa.uint32():
            return DtypeTuple("uint32", "u")
        if pa_type == pa.uint64():
            return DtypeTuple("uint64", "u")
        if pa_type == pa.float32():
            return DtypeTuple("float32", "f")
        if pa_type == pa.float64():
            return DtypeTuple("float64", "f")
        if pa_type == pa.bool_():
            return DtypeTuple("bool", "b")
        return DtypeTuple(str(pa_type), "O")

    @classmethod
    def from_csv_string(cls, str_or_buf: str, separator: str) -> PyarrowWrapper:
        import pyarrow as pa

        if isinstance(str_or_buf, str):
            buf = io.BytesIO(str_or_buf.encode())
        else:
            buf = io.BytesIO(str_or_buf.getvalue().encode())
        return PyarrowWrapper(
            pa.csv.read_csv(buf, read_options=pa.csv.ReadOptions(delimiter=separator))
        )

    def to_csv_string(self, separator: str) -> str:
        lines: list[str] = []
        for a in self._df.to_pylist():
            a: dict[str, Any]
            lines.append(separator.join(str(cell) for cell in a.values()))
        return "\n".join(lines)

    def to_list(self) -> list[list[Any]]:
        return [list(a.values()) for a in self._df.to_pylist()]

    def column_to_array(self, name: str) -> np.ndarray:
        return self._df[name].as_numpy()

    @classmethod
    def from_dict(cls, data: dict) -> DataFrameWrapper:
        import pyarrow as pa

        return PyarrowWrapper(pa.Table.from_pydict(data))

    def write(self, file: str | Path):
        import pyarrow.csv
        import pyarrow.parquet
        import pyarrow.feather

        path = Path(file)
        if path.suffix == ".tsv":
            pyarrow.csv.write_csv(
                self._df, path, write_options=pyarrow.csv.WriteOptions(delimiter="\t")
            )
        elif path.suffix in (".csv", ".txt"):
            pyarrow.csv.write_csv(self._df, path)
        elif path.suffix == ".parquet":
            pyarrow.parquet.write_table(self._df, path)
        elif path.suffix == ".feather":
            pyarrow.feather.write_feather(self._df, path)
        else:
            raise ValueError(
                "Cannot write a pandas dataframe to a file with the given extension "
                f"{path.suffix!r}"
            )


class DtypeTuple(NamedTuple):
    """Normalized dtype description."""

    name: str  # any string representation of dtype
    kind: str  # must follow numpy's kind character


def wrap_dataframe(df) -> DataFrameWrapper:
    if isinstance(df, Mapping):
        return DictWrapper.from_dict(df)
    if is_pandas_dataframe(df):
        return PandasWrapper(df)
    if is_polars_dataframe(df):
        return PolarsWrapper(df)
    if is_pyarrow_table(df):
        return PyarrowWrapper(df)
    if is_narwhals_dataframe(df):
        return wrap_dataframe(df.to_native())
    if isinstance(df, DataFrameWrapper):
        return df
    raise TypeError(f"Unsupported dataframe type: {type(df)}")
