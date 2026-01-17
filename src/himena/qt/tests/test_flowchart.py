import pytest
from himena.qt._qflowchart import iter_next_shift

def test_iter_next_shift():
    it = iter_next_shift(10.0)
    assert next(it) == pytest.approx(0.0)
    assert next(it) == pytest.approx(10.0)
    assert next(it) == pytest.approx(-10.0)
    assert next(it) == pytest.approx(20.0)
    assert next(it) == pytest.approx(-20.0)
    assert next(it) == pytest.approx(30.0)
    assert next(it) == pytest.approx(-30.0)
