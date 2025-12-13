from pathlib import Path

import numpy as np
from himena.data_wrappers import wrap_dataframe, read_csv
import pytest

from himena.types import WidgetDataModel

@pytest.mark.parametrize(
    "mod",
    ["dict", "pandas", "polars", "pyarrow"]
)
def test_read_csv(mod: str, sample_dir: Path, tmpdir):
    df_orig = read_csv(mod, sample_dir / "table.csv")
    df = wrap_dataframe(df_orig)
    repr(df.copy())
    assert df.column_names() == ["a", "b", "c"]
    assert df.column_to_array("a").tolist() == [1, 3, 4, 6, 8]
    assert df.dtypes[0].kind == "i"
    assert df.dtypes[1].kind == "f"
    df_filt = df.filter(np.array([True, False, True, False, True]))
    assert df_filt.shape == (3, 3)
    df.sort("b")
    df.sort("a", descending=True)

    df_cycled_csv = df.from_csv_string(df.to_csv_string())
    assert type(df_cycled_csv) is type(df)
    assert df_cycled_csv.column_names() == ["a", "b", "c"]
    assert df_cycled_csv.column_to_array("a").tolist() == [1, 3, 4, 6, 8]

    df_cycled_dict = df.from_dict(df.to_dict())
    assert df_cycled_dict.column_names() == ["a", "b", "c"]
    assert df_cycled_dict.column_to_array("a").tolist() == [1, 3, 4, 6, 8]

    assert df[0, 0] == 1
    assert df[1:3, 0].tolist() == [3, 4]
    assert df["a"].tolist() == [1, 3, 4, 6, 8]
    df.to_list()

    df_new = df.with_columns({"new": [1, 2, 3, 4, 5]})
    assert df_new.column_names() == ["a", "b", "c", "new"]

    save_dir = Path(tmpdir)
    df.write(save_dir / "table.csv")
    df.write(save_dir / "table.txt")
    df.write(save_dir / "table.tsv")

def test_narwhals():
    import narwhals

    df = narwhals.from_dict(
        {"a": [1, 2, 3], "b": ["p", "q", "r"]}, backend="pandas"
    )
    wrap_dataframe(df)
    wrap_dataframe(WidgetDataModel(value=df, type="dataframe"))
    wrap_dataframe(wrap_dataframe(df))

def test_write_pandas(tmpdir):
    import pandas as pd

    tmpdir = Path(tmpdir)
    df = wrap_dataframe(pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]}))
    for ext in ["csv", "tsv", "txt", "parquet", "feather", "json", "html", "xlsx", "xls", "pickle", "md"]:
        df.write(tmpdir / f"output.{ext}")

def test_write_polars(tmpdir):
    import polars as pl

    tmpdir = Path(tmpdir)
    df = wrap_dataframe(pl.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]}))
    for ext in ["csv", "tsv", "parquet", "json"]:
        df.write(tmpdir / f"output.{ext}")

def test_write_pyarrow(tmpdir):
    import pyarrow as pa

    tmpdir = Path(tmpdir)
    table = pa.table({"a": [1, 2, 3], "b": ["x", "y", "z"]})
    df = wrap_dataframe(table)
    for ext in ["csv", "tsv", "parquet", "feather"]:
        df.write(tmpdir / f"output.{ext}")

def test_dtype_polars():
    import polars as pl

    for dtype_pl, dtype_str, col in [
        (pl.Int8, "i", [-1, 3, 5]),
        (pl.Int16, "i", [-1, 3, 5]),
        (pl.Int32, "i", [-1, 3, 5]),
        (pl.Int64, "i", [-1, 3, 5]),
        (pl.UInt8, "u", [0, 3, 5]),
        (pl.UInt16, "u", [0, 3, 5]),
        (pl.UInt32, "u", [0, 3, 5]),
        (pl.UInt64, "u", [0, 3, 5]),
        (pl.Float32, "f", [-3.2, 0.1, 1.4e3]),
        (pl.Float64, "f", [-3.2, 0.1, 1.4e3]),
        (pl.Float64, "f", [-3.2, 0.1, 1.4e3]),
        (pl.Boolean, "b", [True, False, True]),
        (pl.String, "O", ["a", "b", "c"]),
    ]:
        df = wrap_dataframe(
            pl.DataFrame([pl.Series("a", col, dtype=dtype_pl)])
        )
        df.get_dtype(0).kind == dtype_str

def test_dtype_pyarrow():
    import pyarrow as pa

    for dtype_pa, dtype_str, col in [
        (pa.int8(), "i", [-1, 2, 3]),
        (pa.int16(), "i", [-1, 2, 3]),
        (pa.int32(), "i", [-1, 2, 3]),
        (pa.int64(), "i", [-1, 2, 3]),
        (pa.uint8(), "u", [0, 2, 3]),
        (pa.uint16(), "u", [0, 2, 3]),
        (pa.uint32(), "u", [0, 2, 3]),
        (pa.uint64(), "u", [0, 2, 3]),
        (pa.float32(), "f", [-2.5, 0.0, 3.14]),
        (pa.float64(), "f", [-2.5, 0.0, 3.14]),
        (pa.bool_(), "b", [True, False, True]),
        (pa.string(), "O", ["x", "y", "z"]),
    ]:
        table = pa.table({"a": pa.array(col, type=dtype_pa)})
        df = wrap_dataframe(table)
        df.get_dtype(0).kind == dtype_str
