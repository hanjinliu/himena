from pathlib import Path
import numpy as np
import pytest
import math
from himena.standards import roi, model_meta
from numpy.testing import assert_allclose
from himena import create_image_model

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

def test_image_meta_serialize(tmpdir):
    items = [
        roi.LineRoi(start=(0, 0), end=(6, 3)),
        roi.SegmentedLineRoi(xs=[0, 1.6, 1.6], ys=[0, 0, 2]),
        roi.RectangleRoi(x=2, y=3, width=4, height=5),
        roi.EllipseRoi(x=2, y=3, width=4, height=5),
        roi.PolygonRoi(xs=[0, 1.6, 1.6], ys=[0, 0, 2]),
        roi.PointRoi2D(x=1.4, y=2.3),
        roi.PointsRoi2D(xs=[1.4, 2.3], ys=[2.3, 1.4]),
    ]
    model = create_image_model(
        np.zeros((3, 8, 9)),
        axes=["z", "y", "x"],
        rois=roi.RoiListModel(
            items=items,
            indices=np.arange(len(items)).reshape(-1, 1) % 3,
        ),
    )
    assert isinstance(model.metadata, model_meta.ImageMeta)
    model.metadata.write_metadata(Path(tmpdir))
