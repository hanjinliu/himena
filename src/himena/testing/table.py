from __future__ import annotations

import numpy as np
from numpy.testing import assert_equal
from himena import WidgetDataModel, StandardType
from himena.standards.model_meta import TableMeta
from himena.testing.subwindow import WidgetTester


def test_accepts_table_like(tester: WidgetTester):
    tester.update_model(
        WidgetDataModel(value=[[1, True], ["b", -5.2]], type=StandardType.TABLE)
    )
    assert_equal(tester.to_model().value, [["1", "True"], ["b", "-5.2"]])
    tester.update_model(
        WidgetDataModel(value={"a": [1, 2], "b": [3, 4]}, type=StandardType.TABLE)
    )
    assert_equal(tester.to_model().value, [["a", "b"], ["1", "3"], ["2", "4"]])
    tester.update_model(
        WidgetDataModel(
            value=np.array([[1, 2], [3, 4]], dtype=np.int64), type=StandardType.TABLE
        )
    )
    assert_equal(tester.to_model().value, [["1", "2"], ["3", "4"]])


def test_current_position(tester: WidgetTester):
    tester.update_model(
        WidgetDataModel(
            value=[[1, 2, 3], [4, 5, 6], [7, 8, 9]], type=StandardType.TABLE
        )
    )
    meta = TableMeta(current_position=[1, 2])
    tester.update_model(
        WidgetDataModel(
            value=[[1, 2, 3], [4, 5, 6], [7, 8, 9]],
            metadata=meta,
            type=StandardType.TABLE,
        )
    )
    meta = _cast_meta(tester.to_model().metadata)
    if meta.current_position != [1, 2]:
        raise AssertionError(f"Expected [1, 2], got {meta.current_position!r}")


def test_selections(tester: WidgetTester):
    tester.update_model(
        WidgetDataModel(
            value=[[1, 2, 3], [4, 5, 6], [7, 8, 9]],
            type=StandardType.TABLE,
        )
    )
    meta = _cast_meta(tester.to_model().metadata)
    if meta.selections != []:
        raise AssertionError(f"Expected [], got {meta.selections}")
    meta = TableMeta(selections=[((1, 2), (0, 2))])
    tester.update_model(
        WidgetDataModel(
            value=[[1, 2, 3], [4, 5, 6], [7, 8, 9]],
            metadata=meta,
            type=StandardType.TABLE,
        )
    )
    meta = _cast_meta(tester.to_model().metadata)
    if meta.selections != [((1, 2), (0, 2))]:
        raise AssertionError(f"Expected [((1, 2), (0, 2))], got {meta.selections}")
    meta = TableMeta(selections=[((1, 2), (0, 2)), ((0, 1), (1, 2))])
    tester.update_model(
        WidgetDataModel(
            value=[[1, 2, 3], [4, 5, 6], [7, 8, 9]],
            metadata=meta,
            type=StandardType.TABLE,
        )
    )
    meta = _cast_meta(tester.to_model().metadata)
    if meta.selections != [((1, 2), (0, 2)), ((0, 1), (1, 2))]:
        raise AssertionError(
            f"Expected [((1, 2), (0, 2)), ((0, 1), (1, 2))], got {meta.selections}"
        )


def _cast_meta(meta) -> TableMeta:
    assert isinstance(meta, TableMeta)
    return meta
