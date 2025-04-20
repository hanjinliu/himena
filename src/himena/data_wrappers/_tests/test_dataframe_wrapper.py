from pathlib import Path

import numpy as np
from himena.data_wrappers import wrap_dataframe, read_csv
import pytest

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
