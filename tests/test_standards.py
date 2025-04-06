import numpy as np
import pytest
import math
from himena.standards import roi
from numpy .testing import assert_allclose

def test_line_roi():
    r0 = roi.LineRoi(start=(0, 0), end=(6, 3))
    assert r0.length() == pytest.approx(math.sqrt(6**2 + 3**2))
    xs, ys = r0.arange()
    assert_allclose(xs, np.arange(7) * math.cos(math.atan(3/6)))
    assert_allclose(ys, np.arange(7) * math.sin(math.atan(3/6)))
    xs, ys = r0.linspace(3)
    assert_allclose(xs, [0, 3, 6])
    assert_allclose(ys, [0, 1.5, 3])

def test_segmented_line_roi():
    r0 = roi.SegmentedLineRoi(xs=[0, 1.6, 1.6], ys=[0, 0, 2])
    assert r0.length() == pytest.approx(3.6)
    xs, ys = r0.arange()
    assert_allclose(xs, [0, 1, 1.6, 1.6])
    assert_allclose(ys, [0, 0, 0.4, 1.4])
    xs, ys = r0.linspace(3)
    assert_allclose(xs, [0, 1.6, 1.6])
    assert_allclose(ys, [0, 0.2, 2])
