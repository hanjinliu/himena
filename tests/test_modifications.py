import numpy as np
from numpy.testing import assert_equal
import pytest
from himena import WidgetDataModel, create_model
from himena.consts import StandardType
from himena_builtins import user_modifications as _um


@pytest.mark.parametrize(
    "old, new, char_limit",
    [
        ("abc", "pqr", 1000),
        ("", "\"pq\"\nr\nc", 1000),
        ("abcdefgh", "pqr", 1),
        ("abcd\nefgh\n", "", 1),
        ("123\n456\n78\n234", "12\n99\n456\n234\n999", 1),
        ("\\n\n\n\\n", "\\n\n\\t\n\\n", 1),
    ],
)
def test_reproduce_text_modification(
    old: str,
    new: str,
    char_limit: int,
    monkeypatch,
):
    """Test the reproduce_text_modification function."""
    monkeypatch.setattr(_um, "USE_DIFFLIB_LIMIT", char_limit)
    args = _um.text_modification_tracker(old, new)
    model_old = create_model(old, type=StandardType.TEXT)
    out = _um.reproduce_text_modification(model_old)(args.with_params["diff"])
    assert out.value == new

@pytest.mark.parametrize(
    "old, new, size_limit",
    [
        ([["00", "01"], ["99", "11"]], [["00", "01"], ["10", "11"]], 100),  # edit
        ([[]], [["00", "01"], ["10", "11"]], 100),  # new table
        ([["00", "01"]], [["00"], ["10"]], 100),  # new shape
        ([["00", "01"], ["10", "11"], ["20", "21"]], [["00", "01", "12"], ["10", "11", "12"]], 100),
        ([[]], [["00", "01"], ["10", "11"]], 1),  # new table
        ([["00", "01"]], [["00"], ["10"]], 1),  # new shape
        ([["00", "01"], ["10", "11"], ["20", "21"]], [["00", "01", "12"], ["10", "11", "12"]], 1),
    ],
)
def test_reproduce_table_modification(
    old: list[list[str]],
    new: list[list[str]],
    size_limit: int,
    monkeypatch,
):
    monkeypatch.setattr(_um, "USE_SPARSE_TABLE_DIFF_LIMIT", size_limit)
    old_arr = np.array(old, dtype=np.dtypes.StringDType())
    new_arr = np.array(new, dtype=np.dtypes.StringDType())
    args = _um.table_modification_tracker(old_arr, new_arr)
    model_old = create_model(old_arr, type=StandardType.TABLE)
    out = _um.reproduce_table_modification(model_old)(args.with_params["diff"])
    assert isinstance(out, WidgetDataModel)
    assert_equal(out.value, new_arr)
