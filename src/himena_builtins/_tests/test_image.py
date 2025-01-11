import numpy as np
from qtpy.QtCore import Qt
from himena.standards.model_meta import ImageMeta
from pytestqt.qtbot import QtBot
from himena.testing import WidgetTester, image
from himena_builtins.qt.widgets.image import QImageView


def test_image_view(qtbot: QtBot):
    image_view = QImageView()
    image_view.show()
    with WidgetTester(image_view) as tester:
        # grayscale
        tester.update_model(value=np.arange(100, dtype=np.uint8).reshape(10, 10))
        qtbot.addWidget(image_view)
        assert len(image_view._dims_slider._sliders) == 0

        # 5D with channel
        rng = np.random.default_rng(14442)
        tester.update_model(
            value=rng.random((10, 5, 3, 100, 100), dtype=np.float32),
            metadata=ImageMeta(channel_axis=2)
        )
        image_view._dims_slider._sliders[0]._slider.setValue(1)
        image_view._dims_slider._sliders[2]._slider.setValue(2)

        # switch modes
        qtbot.keyClick(image_view._img_view, Qt.Key.Key_Z)
        qtbot.keyClick(image_view._img_view, Qt.Key.Key_L)
        qtbot.keyClick(image_view._img_view, Qt.Key.Key_L)
        qtbot.keyClick(image_view._img_view, Qt.Key.Key_P)
        qtbot.keyClick(image_view._img_view, Qt.Key.Key_P)
        qtbot.keyClick(image_view._img_view, Qt.Key.Key_R)
        qtbot.keyClick(image_view._img_view, Qt.Key.Key_E)
        qtbot.keyClick(image_view._img_view, Qt.Key.Key_G)

def test_image_view_rgb(qtbot: QtBot):
    image_view = QImageView()
    image_view.show()
    with WidgetTester(image_view) as tester:
        tester.update_model(
            value=np.zeros((100, 100, 3), dtype=np.uint8), metadata=ImageMeta(is_rgb=True),
        )
        assert len(image_view._dims_slider._sliders) == 0
        image_view._control._interp_check_box.setChecked(False)
        image_view._control._interp_check_box.setChecked(True)


def test_image_view_change_dimensionality():
    image.test_change_dimensionality(_get_tester())

def test_image_view_setting_colormap():
    image.test_setting_colormap(_get_tester())

def test_image_view_setting_unit():
    image.test_setting_unit(_get_tester())

def test_image_view_setting_axis_names():
    image.test_setting_axis_names(_get_tester())

def test_image_view_setting_pixel_scale():
    image.test_setting_pixel_scale(_get_tester())

def test_image_view_setting_current_indices():
    image.test_setting_current_indices(_get_tester())

def test_image_view_current_roi():
    image.test_current_roi(_get_tester())

def _get_tester():
    return WidgetTester(QImageView())
