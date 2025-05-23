import math
from himena.standards import roi
import pytest

def test_span_roi():
    r0 = roi.SpanRoi(start=0, end=1)
    r1 = r0.shifted(2)
    assert r1.start == 2
    assert r1.end == 3
    assert r0.width() == 1
    assert r1.width() == 1

def test_point_roi_1d():
    r0 = roi.PointRoi1D(x=0.6)
    r1 = r0.shifted(2)
    assert r1.x == pytest.approx(2.6)

def test_points_roi_1d():
    r0 = roi.PointsRoi1D(xs=[0.6, 1.2])
    r1 = r0.shifted(2)
    assert list(r1.xs) == pytest.approx([2.6, 3.2])

def test_rectangle():
    r0 = roi.RectangleRoi(x=0, y=0, width=1, height=2)
    r1 = r0.shifted(2, 3)
    assert r1.x == 2
    assert r1.y == 3
    assert r1.width == 1
    assert r1.height == 2
    assert r1.area() == 2
    assert r1.to_mask((5, 5)).sum() == 2

def test_rotated_rectangle():
    r0 = roi.RotatedRectangleRoi(start=(1, 1), end=(2, 2), width=1)
    r1 = r0.shifted(2, 3)
    assert r0.length() == pytest.approx(math.sqrt(2), rel=1e-5)
    assert r1.start == (3, 4)
    assert r1.end == (4, 5)
    assert r0.angle() == pytest.approx(-45)
    assert r1.angle_radian() == pytest.approx(-math.pi / 4, rel=1e-5)
    assert r0.to_mask((5, 5)).sum() < 3

def test_ellipse():
    r0 = roi.EllipseRoi(x=0, y=0, width=6, height=8)
    r1 = r0.shifted(2, 3)
    assert r1.x == 2
    assert r1.y == 3
    assert r1.width == 6
    assert r1.height == 8
    assert r0.center() == pytest.approx((3, 4), rel=1e-5)
    assert r1.area() == pytest.approx(math.pi * 3 * 4, rel=1e-5)
    assert r1.to_mask((20, 20)).sum() <= math.pi * 3 * 4
    assert r0.eccentricity() == pytest.approx(math.sqrt(7 / 16), rel=1e-5)
    assert r0.to_mask((20, 20)).sum() <= math.pi * 3 * 4
    assert r0.to_mask((20, 20)).sum() == r1.to_mask((20, 20)).sum()

    # flat ellipse
    rflat = roi.EllipseRoi(x=0, y=4, width=6, height=0)
    assert rflat.area() == 0
    assert rflat.to_mask((20, 20)).sum() == 0
    assert rflat.eccentricity() == 0.0

    rflat = roi.EllipseRoi(x=0, y=4, width=0, height=4)
    assert rflat.area() == 0
    assert rflat.to_mask((20, 20)).sum() == 0
    assert rflat.eccentricity() == 0.0

    rflat = roi.EllipseRoi(x=0, y=4, width=0, height=0)
    assert rflat.area() == 0
    assert rflat.to_mask((20, 20)).sum() == 0
    assert rflat.eccentricity() == 1.0

def test_rotated_ellipse():
    r0 = roi.RotatedEllipseRoi(start=(1, 1), end=(4, 4), width=2)
    r1 = r0.shifted(2, 3)
    assert r0.length() == pytest.approx(3 * math.sqrt(2), rel=1e-5)
    assert r0.area() == pytest.approx(r1.area(), rel=1e-5)
    assert r0.area() == pytest.approx(math.pi * 3 * math.sqrt(2) / 2, rel=1e-5)
    assert r0.eccentricity() == pytest.approx(math.sqrt(7 / 9), rel=1e-5)

def test_circle():
    r0 = roi.CircleRoi(x=0, y=0, radius=5)
    r1 = r0.shifted(10, 8)
    assert r1.x == 10
    assert r1.y == 8
    assert r1.radius == 5
    assert r0.area() == pytest.approx(math.pi * 25, rel=1e-5)
    assert r0.to_mask((20, 20)).sum() < math.pi * 25

def test_point_roi_2d():
    r0 = roi.PointRoi2D(x=0.6, y=1.2)
    r1 = r0.shifted(2, 3)
    assert r1.x == pytest.approx(2.6)
    assert r1.y == pytest.approx(4.2)
    assert r0.bbox().width == 0
    assert r0.to_mask((5, 5)).sum() == 1

def test_points_roi_2d():
    r0 = roi.PointsRoi2D(xs=[0.6, 1.2], ys=[1.2, 2.4])
    r1 = r0.shifted(2, 3)
    assert list(r1.xs) == pytest.approx([2.6, 3.2])
    assert list(r1.ys) == pytest.approx([4.2, 5.4])
    assert r0.bbox().width == pytest.approx(0.6, rel=1e-5)
    assert r0.bbox().height == pytest.approx(1.2, rel=1e-5)
    assert r0.to_mask((5, 5)).sum() == 2
