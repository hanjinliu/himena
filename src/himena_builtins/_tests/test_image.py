import numpy as np
from qtpy import QtCore
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QApplication
from himena.standards.model_meta import ImageMeta
from pytestqt.qtbot import QtBot
from himena.testing import WidgetTester, image
from himena_builtins.qt.widgets.image import QImageView
from himena_builtins.qt.widgets._image_components import _roi_items as _rois

_Ctrl = Qt.KeyboardModifier.ControlModifier

def test_image_view(qtbot: QtBot):
    image_view = QImageView()
    image_view.show()
    image_view._img_view.set_show_labels(True)
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
        image_view._control._channel_mode_combo.setCurrentText("Gray")
        QApplication.processEvents()
        image_view._control._channel_mode_combo.setCurrentText("Mono")
        QApplication.processEvents()
        image_view._control._channel_mode_combo.setCurrentText("Comp.")
        QApplication.processEvents()

        # switch modes
        qtbot.keyClick(image_view._img_view, Qt.Key.Key_Z)
        qtbot.keyPress(image_view._img_view, Qt.Key.Key_Space)
        qtbot.keyRelease(image_view._img_view, Qt.Key.Key_Space)
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
        tester.cycle_model()
        assert len(image_view._dims_slider._sliders) == 0
        image_view._control._interp_check_box.setChecked(False)
        image_view._control._interp_check_box.setChecked(True)
        image_view._control._channel_mode_combo.setCurrentText("Gray")
        QApplication.processEvents()
        image_view._control._channel_mode_combo.setCurrentText("Color")
        QApplication.processEvents()

        tester.update_model(
            value=np.zeros((100, 100, 4), dtype=np.uint8), metadata=ImageMeta(is_rgb=True),
        )
        tester.cycle_model()
        assert len(image_view._dims_slider._sliders) == 0
        image_view._control._interp_check_box.setChecked(False)
        image_view._control._interp_check_box.setChecked(True)
        image_view._control._channel_mode_combo.setCurrentText("Gray")
        QApplication.processEvents()
        image_view._control._channel_mode_combo.setCurrentText("Color")
        QApplication.processEvents()

def test_image_view_draw_roi(qtbot: QtBot):
    image_view = QImageView()
    image_view.show()
    with WidgetTester(image_view) as tester:
        tester.update_model(value=np.zeros((100, 100), dtype=np.uint8))
        qtbot.addWidget(image_view)

        # test ROI drawing
        vp = image_view._img_view.viewport()
        # rectangle
        image_view._img_view.switch_mode(image_view._img_view.Mode.ROI_RECTANGLE)
        qtbot.mousePress(vp, Qt.MouseButton.LeftButton, pos=QtCore.QPoint(10, 10))
        qtbot.mouseMove(vp, pos=QtCore.QPoint(50, 50))
        qtbot.mouseRelease(vp, Qt.MouseButton.LeftButton, pos=QtCore.QPoint(50, 50))
        assert isinstance(image_view._img_view._current_roi_item, _rois.QRectangleRoi)
        qtbot.keyPress(image_view._img_view, Qt.Key.Key_T)
        assert len(image_view._img_view._roi_items) == 1

        # ellipse
        image_view._img_view.switch_mode(image_view._img_view.Mode.ROI_ELLIPSE)
        qtbot.mousePress(vp, Qt.MouseButton.LeftButton, pos=QtCore.QPoint(20, 20))
        qtbot.mouseMove(vp, pos=QtCore.QPoint(50, 50))
        qtbot.mouseRelease(vp, Qt.MouseButton.LeftButton, pos=QtCore.QPoint(50, 50))
        assert isinstance(image_view._img_view._current_roi_item, _rois.QEllipseRoi)

        # line
        image_view._img_view.switch_mode(image_view._img_view.Mode.ROI_LINE)
        qtbot.mousePress(vp, Qt.MouseButton.LeftButton, pos=QtCore.QPoint(10, 10))
        qtbot.mouseMove(vp, pos=QtCore.QPoint(50, 50))
        qtbot.mouseRelease(vp, Qt.MouseButton.LeftButton, pos=QtCore.QPoint(50, 50))
        assert isinstance(image_view._img_view._current_roi_item, _rois.QLineRoi)

        # polygon
        image_view._img_view.switch_mode(image_view._img_view.Mode.ROI_POLYGON)
        qtbot.mouseClick(vp, Qt.MouseButton.LeftButton, pos=QtCore.QPoint(10, 10))
        qtbot.mouseClick(vp, Qt.MouseButton.LeftButton, pos=QtCore.QPoint(10, 20))
        qtbot.mouseClick(vp, Qt.MouseButton.LeftButton, pos=QtCore.QPoint(20, 20))
        qtbot.mouseClick(vp, Qt.MouseButton.LeftButton, pos=QtCore.QPoint(20, 30))
        qtbot.mouseDClick(vp, Qt.MouseButton.LeftButton, pos=QtCore.QPoint(30, 30))
        assert isinstance(image_view._img_view._current_roi_item, _rois.QPolygonRoi)
        qtbot.keyClick(image_view._img_view, Qt.Key.Key_Delete)
        # FIXME: Not working for some reason
        # assert image_view._img_view._current_roi_item is None

def test_image_view_copy_roi(qtbot: QtBot):
    image_view = QImageView()
    image_view.show()
    with WidgetTester(image_view) as tester:
        tester.update_model(value=np.zeros((100, 100), dtype=np.uint8))
        qtbot.addWidget(image_view)

        # draw rectangle
        vp = image_view._img_view.viewport()
        image_view._img_view.switch_mode(image_view._img_view.Mode.ROI_RECTANGLE)
        qtbot.mousePress(vp, Qt.MouseButton.LeftButton, pos=QtCore.QPoint(10, 10))
        qtbot.mouseMove(vp, pos=QtCore.QPoint(50, 50))
        qtbot.mouseRelease(vp, Qt.MouseButton.LeftButton, pos=QtCore.QPoint(50, 50))

        qtbot.keyClick(image_view._img_view, Qt.Key.Key_C, modifier=_Ctrl)
        qtbot.keyClick(image_view._img_view, Qt.Key.Key_V, modifier=_Ctrl)
        assert len(image_view._img_view._roi_items) == 2
        qtbot.keyClick(image_view._img_view, Qt.Key.Key_V, modifier=_Ctrl)
        assert len(image_view._img_view._roi_items) == 3


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