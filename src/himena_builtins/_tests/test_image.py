import warnings
import numpy as np
from qtpy import QtCore
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QApplication
from himena.standards.model_meta import ImageMeta
from pytestqt.qtbot import QtBot
from himena import MainWindow, StandardType
from himena.standards.roi import RoiListModel, LineRoi, PointRoi2D, PointsRoi2D
from himena.standards.roi.core import RectangleRoi
from himena.testing import WidgetTester, image
from himena.types import WidgetDataModel
from himena_builtins.qt.widgets.image import QImageView
from himena_builtins.qt.widgets._image_components import _roi_items as _rois
from himena_builtins.qt.widgets._image_components._control import ComplexMode

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

def test_image_view_roi_collection(qtbot: QtBot):
    image_view = QImageView()
    image_view.show()
    image_view.setSizes([200, 200])
    with WidgetTester(image_view) as tester:
        tester.update_model(
            value=np.zeros((100, 100), dtype=np.uint8),
            metadata=ImageMeta(
                rois=RoiListModel(
                    rois=[
                        LineRoi(indices=(0, 0), name="ROI-0", x1=1, y1=1, x2=4, y2=5),
                        PointRoi2D(indices=(0, 0), name="ROI-1", x=1, y=5),
                    ]
                )
            )
        )
        qtbot.addWidget(image_view)
        image_view._roi_col._roi_visible_btn.click()
        assert image_view._roi_col._roi_visible_btn.isChecked()
        assert not image_view._roi_col._roi_labels_btn.isChecked()
        image_view._roi_col._roi_visible_btn.click()
        assert not image_view._roi_col._roi_visible_btn.isChecked()
        assert not image_view._roi_col._roi_labels_btn.isChecked()
        image_view._roi_col._roi_labels_btn.click()
        assert image_view._roi_col._roi_visible_btn.isChecked()
        assert image_view._roi_col._roi_labels_btn.isChecked()
        image_view._roi_col._list_view._prep_context_menu(
            image_view._roi_col._list_view.model().index(0, 0)
        )
        qtbot.mouseClick(image_view._roi_col._list_view.viewport(), Qt.MouseButton.LeftButton)
        qtbot.mouseMove(image_view._roi_col._list_view.viewport(), QtCore.QPoint(3, 3))
        qtbot.mouseMove(image_view._roi_col._list_view.viewport(), QtCore.QPoint(4, 4))
        image_view._roi_col.remove_selected_rois()


def test_constrast_hist(qtbot: QtBot):
    image_view = QImageView()
    image_view.show()
    with WidgetTester(image_view) as tester:
        tester.update_model(value=np.zeros((100, 100), dtype=np.uint8))
        qtbot.addWidget(image_view)
        control = image_view.control_widget()
        qtbot.addWidget(control)
        control._auto_contrast_btn.click()
        control._histogram.set_clim((1, 2))

def test_complex_image(qtbot: QtBot):
    image_view = QImageView()
    image_view.show()
    yy, xx = np.indices((5, 5))
    img = np.exp(-1j * (yy + xx))
    with WidgetTester(image_view) as tester, warnings.catch_warnings():
        warnings.simplefilter("error")
        tester.update_model(value=img)
        qtbot.addWidget(image_view)
        control = image_view.control_widget()
        qtbot.addWidget(control)
        control.show()
        assert control._complex_mode_combo.isVisible()
        control._complex_mode_combo.setCurrentText(ComplexMode.REAL)
        control._complex_mode_combo.setCurrentText(ComplexMode.IMAG)
        control._complex_mode_combo.setCurrentText(ComplexMode.ABS)
        control._complex_mode_combo.setCurrentText(ComplexMode.LOG_ABS)
        control._complex_mode_combo.setCurrentText(ComplexMode.PHASE)

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

def test_crop_image(himena_ui: MainWindow):
    model = WidgetDataModel(
        value=np.zeros((4, 4, 10, 10)),
        type=StandardType.IMAGE,
        metadata=ImageMeta(
            axes=["t", "z", "y", "x"],
            current_roi=RectangleRoi(indices=(0, 0), x=1, y=1, width=6, height=4),
        ),
    )
    win = himena_ui.add_data_model(model)
    himena_ui.exec_action("builtins:image-crop:crop-image")
    himena_ui.current_window = win
    himena_ui.exec_action(
        "builtins:image-crop:crop-image-multi",
        with_params={"bbox_list": [(1, 1, 4, 5), (1, 5, 2, 2)]}
    )
    himena_ui.current_window = win
    himena_ui.exec_action(
        "builtins:crop-array-nd",
        with_params={"axis_0": (2, 4), "axis_1": (0, 1), "axis_2": (1, 5), "axis_3": (2, 8)},
    )

def test_roi_commands(himena_ui: MainWindow):
    model = WidgetDataModel(
        value=np.zeros((4, 4, 10, 10)),
        type=StandardType.IMAGE,
        metadata=ImageMeta(
            axes=["t", "z", "y", "x"],
            rois=RoiListModel(
                rois=[
                    LineRoi(indices=(0, 0), name="ROI-0", x1=1, y1=1, x2=4, y2=5),
                    PointRoi2D(indices=(0, 0), name="ROI-1", x=1, y=5),
                ]
            ),
        ),
    )
    win = himena_ui.add_data_model(model)
    himena_ui.exec_action("builtins:duplicate-rois")
    assert isinstance(lmodel := himena_ui.current_model.value, RoiListModel)
    assert len(lmodel) == 2
    win_roi = himena_ui.current_window
    himena_ui.exec_action(
        "builtins:filter-image-rois",
        with_params={"types": ["Line"]},
    )
    himena_ui.current_window = win_roi
    himena_ui.exec_action(
        "builtins:select-rois",
        with_params={"selections": [1]},
    )

    # specify
    himena_ui.current_window = win
    himena_ui.exec_action(
        "builtins:image-specify:roi-specify-rectangle",
        with_params={"x": 3, "y": 2, "width": 3.0, "height": 3.0}
    )
    himena_ui.exec_action(
        "builtins:image-specify:roi-specify-ellipse",
        with_params={"x": 3, "y": 2, "width": 3.0, "height": 3.0}
    )
    himena_ui.exec_action(
        "builtins:image-specify:roi-specify-line",
        with_params={"x1": 3, "y1": 2, "x2": 3.0, "y2": 3.0}
    )

    himena_ui.add_object(
        RoiListModel(rois=[PointRoi2D(x=0, y=0), PointsRoi2D(xs=[2, 3], ys=[1, 2])]),
        type=StandardType.ROIS,
    )

    himena_ui.exec_action("builtins:image:point-rois-to-dataframe")
    assert himena_ui.current_model.type == StandardType.DATAFRAME

    # colormap
    model = WidgetDataModel(
        value=np.zeros((4, 2, 10, 10)),
        type=StandardType.IMAGE,
        metadata=ImageMeta(
            axes=["t", "c", "y", "x"],
            channel_axis=1,
        ),
    )

    win = himena_ui.add_data_model(model)
    himena_ui.exec_action("builtins:set-colormaps", with_params={"ch_0": "green", "ch_1": "red"})
    assert isinstance(meta := win.to_model().metadata, ImageMeta)
    assert len(meta.channels) == 2
    assert meta.channels[0].colormap == "cmap:green"
    assert meta.channels[1].colormap == "cmap:red"
    himena_ui.exec_action("builtins:split-channels")
    mod_g = himena_ui.tabs.current()[-2].to_model()
    mod_r = himena_ui.tabs.current()[-1].to_model()
    assert mod_g.metadata.colormap == "cmap:green"
    assert mod_r.metadata.colormap == "cmap:red"
    himena_ui.exec_action("builtins:merge-channels", with_params={"images": [mod_g, mod_r]})
    himena_ui.exec_action(
        "builtins:stack-images",
        with_params={"images": [mod_g, mod_r], "axis_name": "p"}
    )
