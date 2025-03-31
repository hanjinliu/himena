from pathlib import Path
import sys
import numpy as np
from numpy.testing import assert_equal
from himena import create_model
from himena.standards.model_meta import ArrayMeta, DataFrameMeta, DictMeta, TableMeta
from himena.utils.misc import is_subtype
from himena.utils.table_selection import (
    auto_select,
    model_to_xy_arrays,
    model_to_vals_arrays,
    model_to_col_val_arrays
)
import pytest

@pytest.mark.parametrize(
    "input_type, super_type, expected",
    [
        ("text", "text", True),
        ("text.something", "text", True),
        ("text", "text.something", False),
        ("text.something", "text.something", True),
        ("text.something", "text.other", False),
        ("a.b.c.d", "a.b.c", True),
    ],
)
def test_is_subtype(input_type, super_type, expected):
    assert is_subtype(input_type, super_type) == expected

def test_cli_args():
    from himena.utils import cli

    assert cli.to_command_args("rsync", "src", "dst") == ["rsync", "-a", "--progress", "src", "dst"]
    assert cli.to_command_args("rsync", "src", "dst", is_dir=True) == ["rsync", "-ar", "--progress", "src", "dst"]
    assert cli.to_command_args("scp", "src", "dst") == ["scp", "-P", "22", "src", "dst"]
    assert cli.to_command_args("scp", "src", "dst", is_dir=True) == ["scp", "-P", "22", "-r", "src", "dst"]

    if sys.platform == "win32":
        assert cli.to_wsl_path(Path("C:/Users/username")) == "/mnt/c/Users/username"
        assert cli.to_wsl_path(Path("C:/Users/username/")) == "/mnt/c/Users/username"
        assert cli.to_wsl_path(Path("C:/")) == "/mnt/c"
        assert cli.to_wsl_path(Path("C:/Program Files/")) == "/mnt/c/Program Files"
        assert cli.to_wsl_path(Path("D:/")) == "/mnt/d"

    assert cli.local_to_remote("rsync", Path("C:/src"), "dst") == ["rsync", "-a", "--progress", "C:/src", "dst"]
    assert cli.local_to_remote("rsync", Path("C:/src"), "dst", is_dir=True) == ["rsync", "-ar", "--progress", "C:/src", "dst"]
    if sys.platform == "win32":
        assert cli.local_to_remote("rsync", Path("C:/src"), "~/dst", is_wsl=True) == ["wsl", "-e", "rsync", "-a", "--progress", "/mnt/c/src", "~/dst"]

    assert cli.local_to_remote("scp", Path("C:/src"), "dst", port=11) == ["scp", "-P", "11", "C:/src", "dst"]
    assert cli.local_to_remote("scp", Path("C:/src"), "dst", is_dir=True) == ["scp", "-P", "22", "-r", "C:/src", "dst"]
    if sys.platform == "win32":
        assert cli.local_to_remote("scp", Path("C:/src"), "~/dst", is_wsl=True) == ["wsl", "-e", "scp", "-P", "22", "/mnt/c/src", "~/dst"]

    assert cli.remote_to_local("rsync", "src", Path("dst")) == ["rsync", "-a", "--progress", "src", "dst"]
    assert cli.remote_to_local("rsync", "src", Path("dst"), is_dir=True) == ["rsync", "-ar", "--progress", "src", "dst"]
    if sys.platform == "win32":
        assert cli.remote_to_local("rsync", "~/src", Path("C:/dst"), is_wsl=True) == ["wsl", "-e", "rsync", "-a", "--progress", "~/src", "/mnt/c/dst"]

    assert cli.remote_to_local("scp", "src", Path("dst")) == ["scp", "-P", "22", "src", "dst"]
    assert cli.remote_to_local("scp", "src", Path("dst"), is_dir=True) == ["scp", "-P", "22", "-r", "src", "dst"]
    if sys.platform == "win32":
        assert cli.remote_to_local("scp", "~/src", Path("C:/dst"), is_wsl=True) == ["wsl", "-e", "scp", "-P", "22", "~/src", "/mnt/c/dst"]

def test_submodule():
    from himena.utils.entries import is_submodule

    assert is_submodule("himena_builtins.io", "himena_builtins")
    assert is_submodule("himena_builtins.io", "himena_builtins.io")
    assert not is_submodule("himena_builtins.io", "himena_test_plugin.io")

### Table selection tests ###

def _str_array(x):
    return np.array(x, dtype=np.dtypes.StringDType())

@pytest.mark.parametrize(
    "value, meta",
    [
        (_str_array([[1, 11], [2, 12], [3, 13]]), TableMeta()),
        ({"a": [1, 2, 3], "b": [11, 12, 13]}, DataFrameMeta()),
        (np.array([[1, 11], [2, 12], [3, 13]]), ArrayMeta()),
    ]
)
def test_table_selection_auto_select(value, meta):
    model = create_model(value, metadata=meta)
    assert auto_select(model, 1) == [((0, 3), (0, 1))]
    assert auto_select(model, 2) == [((0, 3), (0, 1)), ((0, 3), (1, 2))]
    assert auto_select(model, 3) == [None, ((0, 3), (0, 1)), ((0, 3), (1, 2))]

def test_model_to_arrays():
    model = create_model(
        _str_array([[1, 11, 21], [2, 12, 22], [3, 13, 23]]), metadata=TableMeta()
    )
    x, ys = model_to_xy_arrays(model, ((0, 3), (0, 1)), ((0, 3), (1, 2)))
    assert x.name is None
    assert len(ys) == 1
    assert ys[0].name is None
    assert_equal(x.array, [1, 2, 3])
    assert_equal(ys[0].array, [11, 12, 13])

    with pytest.raises(ValueError):
        model_to_xy_arrays(model, None, ((0, 3), (1, 3)), allow_empty_x=False)
    x, ys = model_to_xy_arrays(model, None, ((0, 3), (1, 3)))
    assert x.name is None
    assert_equal(x.array, [0, 1, 2])
    assert len(ys) == 2
    assert ys[0].name is None
    assert_equal(ys[0].array, [11, 12, 13])
    assert ys[1].name is None
    assert_equal(ys[1].array, [21, 22, 23])

def test_model_to_vals_arrays():
    model = create_model(
        _str_array([[1, 11, 21], [2, 12, 22], [3, 13, 23]]), metadata=TableMeta()
    )
    vals = model_to_vals_arrays(model, [((0, 3), (0, 1)), ((0, 3), (1, 2))])
    assert len(vals) == 2
    assert vals[0].name is None
    assert_equal(vals[0].array, [1, 2, 3])
    assert vals[1].name is None
    assert_equal(vals[1].array, [11, 12, 13])
    model = create_model(
        _str_array([["A", "B", "C"], [1, 11, 21], [2, 12, 22], [3, 13, 23]]),
        metadata=TableMeta(),
    )
    vals = model_to_vals_arrays(
        model, [((0, 4), (0, 1)), ((0, 4), (1, 2))]
    )
    assert len(vals) == 2
    assert vals[0].name == "A"
    assert_equal(vals[0].array, [1, 2, 3])
    assert vals[1].name == "B"
    assert_equal(vals[1].array, [11, 12, 13])

    with pytest.raises(ValueError):
        model_to_vals_arrays(model, [((0, 4), (0, 1)), ((0, 3), (1, 2))])
    model_to_vals_arrays(model, [((0, 4), (0, 1)), ((0, 3), (1, 2))], same_size=False)

def test_model_to_col_val_arrays():
    model = create_model(
        _str_array([[1, 11, "a"], [2, 12, "a"], [3, 13, "b"]]), metadata=TableMeta()
    )
    col, val = model_to_col_val_arrays(model, ((0, 3), (2, 3)), ((0, 3), (0, 1)))
    assert col.name is None
    assert_equal(col.array, ["a", "a", "b"])
    assert val.name is None
    assert_equal(val.array, [1, 2, 3])
