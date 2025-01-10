from himena.testing import WidgetTester, image
from himena_builtins.qt.widgets.image import QImageView

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
