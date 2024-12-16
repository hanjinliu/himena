from __future__ import annotations

from cmap import Colormap
import numpy as np
from numpy.testing import assert_allclose
import pytest
from himena import WidgetDataModel, StandardType
from himena.widgets import MainWindow
from himena.standards.model_meta import ImageChannel, ImageMeta, ArrayAxis
from himena.standards import roi as _roi


def test_setting_colormap(ui: MainWindow):
    win = ui.add_data_model(_zyx_image_model())
    model = win.to_model()
    meta = _cast_meta(model.metadata)
    assert len(meta.channels) == 1
    assert Colormap(meta.channels[0].colormap) == Colormap("gray")

    win.update_model(_zyx_image_model(colormap="green"))
    model = win.to_model()
    meta = _cast_meta(model.metadata)
    if len(meta.channels) != 1:
        raise AssertionError(f"Expected 1 channel, got {len(meta.channels)}")
    if Colormap(meta.channels[0].colormap) != Colormap("green"):
        raise AssertionError(
            f"Expected {Colormap('green')}, got {meta.channels[0].colormap}"
        )


def test_setting_unit(ui: MainWindow):
    win = ui.add_data_model(_zyx_image_model())
    model = win.to_model()
    meta = _cast_meta(model.metadata)
    if meta.unit != "a.u.":
        raise AssertionError(f"Expected 'a.u.', got {meta.unit}")

    win.update_model(_zyx_image_model(unit="mV"))
    model = win.to_model()
    meta = _cast_meta(model.metadata)
    if meta.unit != "mV":
        raise AssertionError(f"Expected 'mV', got {meta.unit}")


def test_setting_pixel_scale(ui: MainWindow):
    win = ui.add_data_model(_zyx_image_model())
    model = win.to_model()
    meta = _cast_meta(model.metadata)
    assert len(meta.axes) == 3
    if any(axis.scale != pytest.approx(1.0) for axis in meta.axes):
        raise AssertionError(
            f"Expected scales [1.0, 1.0, 1.0], got {[axis.scale for axis in meta.axes]}"
        )

    scales = [0.1, 0.2, 0.3]
    win.update_model(_zyx_image_model(pixel_scale=scales))
    model = win.to_model()
    meta = _cast_meta(model.metadata)
    assert meta.axes is not None
    assert len(meta.axes) == 3
    if any(
        axis.scale != pytest.approx(scale) for axis, scale in zip(meta.axes, scales)
    ):
        raise AssertionError(
            f"Expected scales {scales}, got {[axis.scale for axis in meta.axes]}"
        )


def test_setting_axis_names(ui: MainWindow):
    win = ui.add_data_model(_zyx_image_model())
    model = win.to_model()
    meta = _cast_meta(model.metadata)
    assert len(meta.axes) == 3
    if any(axis.name != name for axis, name in zip(meta.axes, ["z", "y", "x"])):
        raise AssertionError(
            f"Expected names ['z', 'y', 'x'], got {[axis.name for axis in meta.axes]}"
        )

    names = ["t", "y", "x"]
    win.update_model(_zyx_image_model(axis_names=names))
    model = win.to_model()
    meta = _cast_meta(model.metadata)
    assert meta.axes is not None
    assert len(meta.axes) == 3
    if any(axis.name != name for axis, name in zip(meta.axes, names)):
        raise AssertionError(
            f"Expected names {names}, got {[axis.name for axis in meta.axes]}"
        )


def test_setting_current_indices(ui: MainWindow):
    win = ui.add_data_model(_zyx_image_model())
    model = win.to_model()
    meta = _cast_meta(model.metadata)
    if meta.current_indices != (0, slice(None), slice(None)):
        raise AssertionError(
            f"Expected (0, slice(None), slice(None)), got {meta.current_indices}"
        )

    win.update_model(_zyx_image_model(current_indices=(1, slice(None), slice(None))))
    model = win.to_model()
    meta = _cast_meta(model.metadata)
    if meta.current_indices != (1, slice(None), slice(None)):
        raise AssertionError(
            f"Expected (1, slice(None), slice(None)), got {meta.current_indices}"
        )


def test_current_roi(ui: MainWindow):
    win = ui.add_data_model(_zyx_image_model())
    model = win.to_model()
    meta = _cast_meta(model.metadata)
    assert meta.current_roi is None

    roi = _roi.RectangleRoi(indices=(1,), x=2.9, y=0, width=2, height=2.5)
    win.update_model(
        _zyx_image_model(current_roi=roi, current_indices=(1, slice(None), slice(None)))
    )
    model = win.to_model()
    meta = _cast_meta(model.metadata)
    assert meta.current_roi is not None
    croi = meta.current_roi
    assert isinstance(croi, _roi.RectangleRoi)
    assert croi.indices == (1,), croi.indices
    assert_allclose([croi.x, croi.y, croi.width, croi.height], [2.9, 0, 2, 2.5])


def test_change_dimensionality(ui: MainWindow):
    """Check changing the dimensionality of the image works."""
    win = ui.add_data_model(immodel(np.arange(15).reshape(3, 5)))
    assert win.to_model().value.shape == (3, 5)
    assert not win.to_model().metadata.is_rgb
    win.update_model(immodel(np.arange(24).reshape(4, 6)))
    assert win.to_model().value.shape == (4, 6)
    assert not win.to_model().metadata.is_rgb
    win.update_model(immodel(np.arange(96).reshape(4, 4, 6)))
    assert win.to_model().value.shape == (4, 4, 6)
    assert not win.to_model().metadata.is_rgb


def test_rgb_images(ui: MainWindow):
    """Check that RGB images are handled correctly."""
    meta = ImageMeta(is_rgb=True)
    win = ui.add_data_model(
        immodel(np.full((5, 5, 3), 200, dtype=np.uint8), metadata=meta),
    )
    assert win.to_model().value.shape == (5, 5, 3)
    assert win.to_model().metadata.is_rgb
    win.update_model(immodel(np.full((4, 6, 3), 200, dtype=np.uint8), metadata=meta))
    assert win.to_model().value.shape == (4, 6, 3)
    assert win.to_model().metadata.is_rgb
    win.update_model(immodel(np.full((4, 6), 100, dtype=np.uint8)))
    assert win.to_model().value.shape == (4, 6)
    assert not win.to_model().metadata.is_rgb


def _cast_meta(meta) -> ImageMeta:
    assert isinstance(meta, ImageMeta)
    return meta


def _zyx_image_model(
    axis_names: list[str] = ["z", "y", "x"],
    pixel_scale: list[float] = [1.0, 1.0, 1.0],
    pixel_unit: str = "um",
    colormap: str = "gray",
    unit: str = "a.u.",
    current_indices=(0, slice(None), slice(None)),
    current_roi: _roi.ImageRoi | None = None,
) -> WidgetDataModel:
    axes = [
        ArrayAxis(name=name, scale=scale, unit=pixel_unit)
        for name, scale in zip(axis_names, pixel_scale)
    ]
    channels = [ImageChannel(colormap=Colormap(colormap))]
    return WidgetDataModel(
        value=np.arange(48).reshape(3, 4, 4),
        type=StandardType.IMAGE,
        metadata=ImageMeta(
            axes=axes,
            unit=unit,
            channels=channels,
            current_indices=current_indices,
            current_roi=current_roi,
            is_rgb=False,
        ),
    )


def immodel(value, metadata=None) -> WidgetDataModel[np.ndarray]:
    return WidgetDataModel(value=value, type=StandardType.IMAGE, metadata=metadata)
