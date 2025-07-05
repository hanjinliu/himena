from pathlib import Path
import sys
import warnings
import numpy as np
from numpy.testing import assert_equal
from himena import create_model
from himena.standards.model_meta import ArrayMeta, DataFrameMeta, DictMeta, TableMeta
from himena.types import Size, WindowRect
from himena.utils.misc import is_subtype
from himena.utils.table_selection import (
    auto_select,
    model_to_xy_arrays,
    model_to_vals_arrays,
    model_to_col_val_arrays
)
from himena.utils.collections import OrderedSet, FrozenList, UndoRedoStack
from himena.utils.ndobject import NDObjectCollection
from himena.utils.window_rect import ResizeState
import pytest

def test_ordered_set():
    oset = OrderedSet()
    oset.add(1)
    oset.add(2)
    assert len(oset) == 2
    assert list(oset) == [1, 2]
    assert 1 in oset
    assert 3 not in oset
    repr(oset)

def test_frozen_list():
    flist = FrozenList([1, 2, 3])
    assert len(flist) == 3
    assert flist[0] == 1
    assert flist[1] == 2
    assert flist[2] == 3
    assert flist.index(2) == 1
    assert flist.count(2) == 1
    repr(flist)

def test_undo_redo_stack():
    stack = UndoRedoStack(size=3)
    stack.push(1)
    stack.push(2)
    stack.push(3)
    assert len(stack._stack_undo) == 3
    assert len(stack._stack_redo) == 0
    stack.push(4)
    assert len(stack._stack_undo) == 3
    assert len(stack._stack_redo) == 0
    assert stack.undoable()
    assert not stack.redoable()
    assert stack.undo() == 4
    assert len(stack._stack_undo) == 2
    assert len(stack._stack_redo) == 1
    assert stack.redoable()
    assert stack.redo() == 4
    assert len(stack._stack_undo) == 3
    assert len(stack._stack_redo) == 0
    assert stack.undo() == 4
    assert stack.undo() == 3
    assert stack.undo() == 2
    assert stack.undo() is None
    stack.clear()
    assert len(stack._stack_undo) == 0
    assert len(stack._stack_redo) == 0
    assert stack.redo() is None

def test_ndobject_collection():
    ndo = NDObjectCollection(
        items=["a", "b", "c"],
        indices=np.array([[0, 0], [0, 1], [1, 0]]),
        axis_names=["t", "z"],
    )
    ndo.set_axis_names(["frame", "slice"])
    assert ndo.axis_names == ["frame", "slice"]
    ndo_coerced = ndo.coerce_dimensions(["additional", "frame", "slice"])
    assert ndo_coerced.axis_names == ["additional", "frame", "slice"]
    assert ndo_coerced.items.tolist() == ["a", "b", "c"]
    assert ndo_coerced.indices.tolist() == [[-1, 0, 0], [-1, 0, 1], [-1, 1, 0]]
    ndo_copy = ndo.copy()
    assert ndo_copy.pop(1) == "b"
    assert len(ndo_copy) == 2
    assert len(ndo) == 3
    ndo_proj = ndo_copy.project(0)
    assert len(ndo_proj) == 2
    assert ndo_proj.items.tolist() == ["a", "c"]
    assert ndo_proj.axis_names == ["slice"]
    ndo.simplified()

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
    assert auto_select(model, 1) == [((0, None), (0, 1))]
    assert auto_select(model, 2) == [((0, None), (0, 1)), ((0, None), (1, 2))]
    assert auto_select(model, 3) == [None, ((0, None), (0, 1)), ((0, None), (1, 2))]

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

    model = create_model(
        {"c0": [1, 2, 3], "c1": ["t", "s", "t"]}, metadata=DataFrameMeta()
    )
    col, val = model_to_col_val_arrays(model, ((0, 3), (1, 2)), ((0, 3), (0, 1)))
    assert col.name == "c1"
    assert_equal(col.array, ["t", "s", "t"])
    assert val.name == "c0"
    assert_equal(val.array, [1, 2, 3])

@pytest.mark.parametrize(
    "state",
    [state for state in ResizeState]
)
def test_resize(state: ResizeState):
    state.resize_widget(WindowRect(10, 20, 40, 33), (30, 38), Size(3, 3), Size(100, 100))

def test_exception():
    from himena.exceptions import ExceptionHandler

    handler = ExceptionHandler(lambda *_: None, lambda *_: None)
    with pytest.raises(ValueError):
        with handler:
            raise ValueError("Test exception")

    with handler:
        warnings.warn("Test warning", UserWarning, stacklevel=2)
