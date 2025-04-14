import warnings
import numpy as np
from numpy.testing import assert_equal
from pathlib import Path
from qtpy import QtCore
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QApplication
from himena.standards.model_meta import ArrayAxis, ImageMeta
from pytestqt.qtbot import QtBot
from himena import MainWindow, StandardType, create_image_model
from himena.standards.roi import RoiListModel, LineRoi, PointRoi2D, PointsRoi2D
from himena.standards.roi.core import RectangleRoi
from himena.testing import WidgetTester, image, file_dialog_response
from himena.types import WidgetDataModel
from himena_builtins.qt.widgets.image import QImageView, QImageLabelView
from himena_builtins.qt.widgets._image_components import _roi_items as _rois
from himena_builtins.qt.widgets._image_components._control import ComplexMode
from himena_builtins.tools.image import _make_roi_limits_getter, _bbox_list_getter
from himena_builtins.qt.widgets._image_components._handles import RoiSelectionHandles

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
        image_view._control._chn_mode_combo.setCurrentText("Gray")
        QApplication.processEvents()
        image_view._control._chn_mode_combo.setCurrentText("Mono")
        QApplication.processEvents()
        image_view._control._chn_mode_combo.setCurrentText("Comp.")
        QApplication.processEvents()
        image_view._control._histogram._line_low._show_value_label()

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

        # click sliders
        slider = image_view._dims_slider._sliders[0]
        assert not slider._edit_value_line.isVisible()
        qtbot.mouseDClick(slider._index_label, Qt.MouseButton.LeftButton)
        assert slider._edit_value_line.isVisible()
        qtbot.keyClick(slider._edit_value_line, Qt.Key.Key_Escape)
        assert not slider._edit_value_line.isVisible()
        qtbot.mouseDClick(slider._index_label, Qt.MouseButton.LeftButton)
        assert slider._edit_value_line.isVisible()
        slider._edit_value_line.setText("2")
        qtbot.keyClick(slider._edit_value_line, Qt.Key.Key_Return)
        assert not slider._edit_value_line.isVisible()
        assert slider._slider.value() == 2

        image_view._img_view._make_menu_for_view()

def test_image_labels_view(qtbot: QtBot):
    image_view = QImageLabelView()
    image_view.show()
    with WidgetTester(image_view) as tester:
        tester.update_model(value=np.arange(24, dtype=np.uint8).reshape(2, 3, 4))
        qtbot.addWidget(image_view)
        assert len(image_view._dims_slider._sliders) == 1

        image_view._dims_slider._sliders[0]._slider.setValue(1)

def test_image_view_rgb(qtbot: QtBot):
    image_view = QImageView()
    image_view.show()
    with WidgetTester(image_view) as tester:
        tester.update_model(
            value=np.zeros((100, 100, 3), dtype=np.uint8), metadata=ImageMeta(is_rgb=True),
        )
        qtbot.addWidget(image_view)
        tester.cycle_model()
        assert len(image_view._dims_slider._sliders) == 0
        image_view._control._interp_check_box.setChecked(False)
        image_view._control._interp_check_box.setChecked(True)
        image_view._control._chn_mode_combo.setCurrentText("Gray")
        QApplication.processEvents()
        image_view._control._chn_mode_combo.setCurrentText("Color")
        QApplication.processEvents()

        tester.update_model(
            value=np.zeros((100, 100, 4), dtype=np.uint8), metadata=ImageMeta(is_rgb=True),
        )
        tester.cycle_model()
        assert len(image_view._dims_slider._sliders) == 0
        image_view._control._interp_check_box.setChecked(False)
        image_view._control._interp_check_box.setChecked(True)
        image_view._control._chn_mode_combo.setCurrentText("Gray")
        QApplication.processEvents()
        image_view._control._chn_mode_combo.setCurrentText("Color")
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
        image_view._img_view._make_menu_for_roi(image_view._img_view._roi_items[0])

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
        qtbot.mouseClick(vp, Qt.MouseButton.LeftButton, pos=QtCore.QPoint(30, 10))
        # line should be removed by clicking somewhere else
        assert image_view._img_view._current_roi_item is None

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

def test_image_view_copy_roi(himena_ui: MainWindow, qtbot: QtBot):
    image_view = QImageView()
    himena_ui.add_widget(image_view)
    himena_ui.show()
    with WidgetTester(image_view) as tester:
        tester.update_model(value=np.zeros((100, 100), dtype=np.uint8))
        qtbot.addWidget(image_view)

        # draw rectangle
        vp = image_view._img_view.viewport()
        image_view._img_view.switch_mode(image_view._img_view.Mode.ROI_RECTANGLE)
        qtbot.mousePress(vp, Qt.MouseButton.LeftButton, pos=QtCore.QPoint(10, 10))
        qtbot.mouseMove(vp, pos=QtCore.QPoint(50, 50))
        qtbot.mouseRelease(vp, Qt.MouseButton.LeftButton, pos=QtCore.QPoint(50, 50))

        qtbot.keyClick(image_view, Qt.Key.Key_C, modifier=_Ctrl)
        image_view._img_view.standard_ctrl_key_press(Qt.Key.Key_V)
        assert len(image_view._img_view._roi_items) == 2
        image_view._img_view.standard_ctrl_key_press(Qt.Key.Key_V)
        assert len(image_view._img_view._roi_items) == 3

def test_image_view_copy_roi_from_window_to_window(himena_ui: MainWindow, qtbot: QtBot):
    image_view_0 = QImageView()
    image_view_1 = QImageView()
    himena_ui.add_widget(image_view_0)
    himena_ui.add_widget(image_view_1)
    himena_ui.show()
    with (
        WidgetTester(image_view_0) as tester_0,
        WidgetTester(image_view_1) as tester_1
    ):
        tester_0.update_model(
            value=np.zeros((100, 100), dtype=np.uint8),
            metadata=ImageMeta(
                rois=RoiListModel(
                    items=[LineRoi(name="ROI-0", start=(1, 1), end=(4, 5),)],
                )
            )
        )
        tester_1.update_model(value=np.zeros((100, 100), dtype=np.uint8))
        qtbot.addWidget(image_view_0)
        qtbot.addWidget(image_view_1)
        image_view_0._roi_col._list_view.set_selection([0])
        qtbot.keyClick(image_view_0, Qt.Key.Key_C, modifier=_Ctrl)
        image_view_1._img_view.standard_ctrl_key_press(Qt.Key.Key_V)
        assert len(image_view_0._img_view._roi_items) == 1
        assert len(image_view_1._img_view._roi_items) == 1
        qtbot.keyClick(image_view_1._roi_col._list_view, Qt.Key.Key_V, modifier=_Ctrl)
        assert len(image_view_0._img_view._roi_items) == 1
        assert len(image_view_1._img_view._roi_items) == 2


def test_image_view_select_roi(qtbot: QtBot):
    image_view = QImageView()
    image_view.resize(150, 150)
    image_view.show()
    image_view.setSizes([300, 100])
    with WidgetTester(image_view) as tester:
        tester.update_model(value=np.zeros((100, 100), dtype=np.uint8))
        qtbot.addWidget(image_view)
        view = image_view._img_view
        view._wheel_event(1)
        view._wheel_event(-1)
        # point
        view._current_roi_item = _rois.QPointRoi(2, 3)
        view.select_item_at(QtCore.QPointF(2, 3))
        assert isinstance(view._current_roi_item, _rois.QPointRoi)
        view.select_item_at(QtCore.QPointF(10, 10))
        assert view._current_roi_item is None

        # points
        view._current_roi_item = _rois.QPointsRoi([2, 4], [3, 4])
        view.select_item_at(QtCore.QPointF(2, 3))
        assert isinstance(view._current_roi_item, _rois.QPointsRoi)
        view.select_item_at(QtCore.QPointF(10, 10))
        assert view._current_roi_item is None

        # line
        view._current_roi_item = _rois.QLineRoi(0, 0, 3, 3)
        view.select_item_at(QtCore.QPointF(1, 1))
        assert isinstance(view._current_roi_item, _rois.QLineRoi)
        view.select_item_at(QtCore.QPointF(3, 0))
        assert view._current_roi_item is None

        # rectangle
        view._current_roi_item = _rois.QRectangleRoi(0, 0, 3, 3)
        view.select_item_at(QtCore.QPointF(1, 2))
        assert isinstance(view._current_roi_item, _rois.QRectangleRoi)
        view.select_item_at(QtCore.QPointF(10, 2))
        assert view._current_roi_item is None

        # ellipse
        view._current_roi_item = _rois.QEllipseRoi(0, 0, 3, 5)
        view.select_item_at(QtCore.QPointF(1, 2))
        assert isinstance(view._current_roi_item, _rois.QEllipseRoi)
        view.select_item_at(QtCore.QPointF(0, 4))
        # assert view._current_roi_item is None  # FIXME: Not working for some reason

        # polygon
        view._current_roi_item = _rois.QPolygonRoi([0, 1, 3, 0], [3, 5, 5, 3])
        view.select_item_at(QtCore.QPointF(1, 5))
        assert isinstance(view._current_roi_item, _rois.QPolygonRoi)
        view.select_item_at(QtCore.QPointF(6, 3))
        assert view._current_roi_item is None

        # segmented line
        view._current_roi_item = _rois.QSegmentedLineRoi([0, 1, 3], [3, 5, 5])
        view.select_item_at(QtCore.QPointF(1, 5))
        assert isinstance(view._current_roi_item, _rois.QSegmentedLineRoi)
        view.select_item_at(QtCore.QPointF(6, 3))
        assert view._current_roi_item is None

        # rotated rectangle
        view._current_roi_item = _rois.QRotatedRectangleRoi(
            QtCore.QPointF(0, 0),
            QtCore.QPointF(10, 10),
            6,
        )
        view.select_item_at(QtCore.QPointF(4, 4))
        assert isinstance(view._current_roi_item, _rois.QRotatedRectangleRoi)
        view.select_item_at(QtCore.QPointF(10, 0))
        assert view._current_roi_item is None

        image_view._roi_col._roi_labels_btn.click()
        QApplication.processEvents()
        assert image_view._roi_col._roi_visible_btn.isChecked()
        assert not image_view._roi_col._roi_labels_btn.isChecked()
        image_view._roi_col._roi_visible_btn.click()
        QApplication.processEvents()
        assert not image_view._roi_col._roi_visible_btn.isChecked()
        assert not image_view._roi_col._roi_labels_btn.isChecked()
        image_view._roi_col._roi_labels_btn.click()
        QApplication.processEvents()
        assert image_view._roi_col._roi_visible_btn.isChecked()
        assert image_view._roi_col._roi_labels_btn.isChecked()
        image_view._roi_col._list_view._prep_context_menu(
            image_view._roi_col._list_view.model().index(0, 0)
        )
        qtbot.mouseClick(image_view._roi_col._list_view.viewport(), Qt.MouseButton.LeftButton)
        qtbot.mouseMove(image_view._roi_col._list_view.viewport(), QtCore.QPoint(3, 3))
        qtbot.mouseMove(image_view._roi_col._list_view.viewport(), QtCore.QPoint(4, 4))
        image_view._roi_col.remove_selected_rois()
        QApplication.processEvents()
        image_view._img_view.set_current_roi(_rois.QPolygonRoi([0, 1, 3, 0], [3, 5, 5, 3]))
        QApplication.processEvents()
        image_view._img_view.remove_current_item()

def test_image_view_roi_selection_from_list_widget(qtbot: QtBot):
    """Check if clicking ROIs from the QRoiCollection works as expected."""
    image_view = QImageView()
    image_view.setSizes([300, 100])
    with WidgetTester(image_view) as tester:
        tester.update_model(
            value=np.zeros((100, 100), dtype=np.uint8),
            metadata=ImageMeta(
                rois=RoiListModel(
                    items=[
                        LineRoi(name="ROI-0", start=(1, 1), end=(4, 5)),
                        PointRoi2D(name="ROI-1", x=1, y=5),
                    ],
                ),
            ),
        )
        qtbot.addWidget(image_view)
        assert image_view._roi_col.count() == 2
        list_view = image_view._roi_col._list_view
        image_view._roi_col._on_item_clicked(list_view.model().index(0, 0))
        assert isinstance(image_view._img_view._current_roi_item, _rois.QLineRoi)
        image_view._roi_col._on_item_clicked(list_view.model().index(1, 0))
        assert isinstance(image_view._img_view._current_roi_item, _rois.QPointRoi)
        assert len(image_view._img_view._roi_items) == 2
        assert any(isinstance(item, _rois.QLineRoi) for item in image_view._img_view.items())
        assert any(isinstance(item, _rois.QPointRoi) for item in image_view._img_view.items())

def test_image_view_roi_actions(qtbot: QtBot):
    image_view = QImageView()
    image_view.setSizes([300, 100])
    with WidgetTester(image_view) as tester:
        tester.update_model(
            value=np.zeros((5, 2, 30, 30), dtype=np.uint8),
            metadata=ImageMeta(
                axes=[ArrayAxis(name=name) for name in ["t", "c", "y", "x"]],
                rois=RoiListModel(
                    items=[
                        LineRoi(name="ROI-0", start=(1, 1), end=(4, 5)),
                        PointRoi2D(name="ROI-1", x=1, y=5),
                        RectangleRoi(name="ROI-2", x=1, y=1, width=3, height=4),
                    ],
                    indices=np.array([[0, 0], [1, 0], [0, 1]], dtype=np.int32),
                    axis_names=["t", "c"],
                ),
            ),
        )
        qtbot.addWidget(image_view)
        assert image_view._roi_col.count() == 3
        image_view._roi_col.flatten_roi(0)
        image_view._roi_col.flatten_roi_along(1, axis=1)
        image_view._roi_col.move_roi(2, (3, 0))
        meta = tester.to_model().metadata
        assert isinstance(meta, ImageMeta)
        assert_equal(meta.unwrap_rois().indices, [[-1, -1], [1, -1], [3, 0]])
        opt = image_view._roi_col._list_view._options_for_select_dimensions()
        dlg, container = image_view._roi_col._list_view._make_dialog(opt)
        qtbot.addWidget(dlg)
        assert len(container) == 2
        assert container[0].label == "t"
        assert container[1].label == "c"

def test_constrast_hist(qtbot: QtBot):
    image_view = QImageView()
    image_view.show()
    with WidgetTester(image_view) as tester:
        tester.update_model(value=np.zeros((100, 100), dtype=np.uint8))
        qtbot.addWidget(image_view)
        control = image_view.control_widget()
        qtbot.addWidget(control)
        control._auto_cont_btn.click()
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
        assert control._cmp_mode_combo.isVisible()
        control._cmp_mode_combo.setCurrentText(ComplexMode.REAL)
        control._cmp_mode_combo.setCurrentText(ComplexMode.IMAG)
        control._cmp_mode_combo.setCurrentText(ComplexMode.ABS)
        control._cmp_mode_combo.setCurrentText(ComplexMode.LOG_ABS)
        control._cmp_mode_combo.setCurrentText(ComplexMode.PHASE)

def test_image_view_change_dimensionality(qtbot: QtBot):
    image.test_change_dimensionality(_get_tester())

def test_image_view_setting_colormap(qtbot: QtBot):
    image.test_setting_colormap(_get_tester())

def test_image_view_setting_unit(qtbot: QtBot):
    image.test_setting_unit(_get_tester())

def test_image_view_setting_axis_names(qtbot: QtBot):
    image.test_setting_axis_names(_get_tester())

def test_image_view_setting_pixel_scale(qtbot: QtBot):
    image.test_setting_pixel_scale(_get_tester())

def test_image_view_setting_current_indices(qtbot: QtBot):
    image.test_setting_current_indices(_get_tester())

def test_image_view_current_roi(qtbot: QtBot):
    image.test_current_roi(_get_tester())

def _get_tester():
    return WidgetTester(QImageView())

def test_crop_image(himena_ui: MainWindow, tmpdir):
    model = create_image_model(
        np.zeros((4, 4, 10, 10)),
        axes=["t", "z", "y", "x"],
        current_roi=RectangleRoi(indices=(0, 0), x=1, y=1, width=6, height=4),
    )
    win = himena_ui.add_data_model(model)
    himena_ui.exec_action("builtins:image-crop:crop-image")
    himena_ui.exec_action("builtins:image-capture:copy-slice-to-clipboard")
    with file_dialog_response(himena_ui, Path(tmpdir) / "tmp.png"):
        himena_ui.exec_action("builtins:image-capture:save-slice")
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

    # multi-channel image
    model = create_image_model(
        np.zeros((4, 3, 10, 10)),
        axes=["t", "c", "y", "x"],
        current_roi=RectangleRoi(indices=(0, 0), x=1, y=1, width=6, height=4),
        channel_axis=1,
    )
    win = himena_ui.add_data_model(model)
    himena_ui.exec_action("builtins:image-crop:crop-image")
    himena_ui.exec_action("builtins:image-capture:copy-slice-to-clipboard")
    with file_dialog_response(himena_ui, Path(tmpdir) / "tmp.png"):
        himena_ui.exec_action("builtins:image-capture:save-slice")
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

    # test limit getters
    model = win.to_model()
    _bbox_list_getter(model.metadata, model.value)()
    _make_roi_limits_getter(win, "x")()
    _make_roi_limits_getter(win, "y")()

def test_image_view_commands(himena_ui: MainWindow, tmpdir):
    himena_ui.add_data_model(
        WidgetDataModel(
            value=np.zeros((20, 20)),
            type=StandardType.IMAGE,
        )
    )
    himena_ui.exec_action("builtins:image:set-zoom-factor", with_params={"scale": 100.0})
    himena_ui.exec_action("builtins:image-screenshot:copy-viewer-screenshot")
    with file_dialog_response(himena_ui, Path(tmpdir) / "tmp.png") as save_path:
        himena_ui.exec_action("builtins:image-screenshot:save-viewer-screenshot")
        assert save_path.exists()


def test_roi_commands(himena_ui: MainWindow):
    model = create_image_model(
        np.zeros((4, 4, 10, 10)),
        axes=["t", "z", "y", "x"],
        rois=RoiListModel(
            items=[
                LineRoi(name="ROI-0", start=(1, 1), end=(4, 5)),
                PointRoi2D(name="ROI-1", x=1, y=5),
            ],
            indices=np.array([[0, 0], [0, 0]], dtype=np.int32),
            axis_names=["t", "z"],
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
        RoiListModel(
            [PointRoi2D(x=0, y=0), PointsRoi2D(xs=[2, 3], ys=[1, 2])],
        ),
        type=StandardType.ROIS,
    )

    himena_ui.exec_action("builtins:image:point-rois-to-dataframe")
    assert himena_ui.current_model.type == StandardType.DATAFRAME

    # colormap
    model = create_image_model(
        np.zeros((4, 2, 10, 10)),
        axes=["t", "c", "y", "x"],
        channel_axis=1,
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

def test_rgb(himena_ui: MainWindow):
    model = create_image_model(
        np.zeros((10, 10, 3)),
        axes=["y", "x", "c"],
        is_rgb=True,
    )
    win = himena_ui.add_data_model(model)
    assert isinstance(view := win.widget, QImageView)
    assert view._is_rgb
    himena_ui.exec_action("builtins:split-channels")
    assert len(himena_ui.tabs.current()) == 4

def test_scale_bar(himena_ui: MainWindow):
    win = himena_ui.add_data_model(
        create_image_model(
            np.zeros((100, 100)),
            axes=[
                ArrayAxis(name="y", scale=0.42, unit="um"),
                ArrayAxis(name="x", scale=0.28, unit="um")
            ]
        )
    )
    himena_ui.exec_action("builtins:image:setup-image-scale-bar", with_params={})
    himena_ui.show()
    win.size = (300, 300)
    win.size = (200, 200)
    assert isinstance(win.widget, QImageView)
    win.widget._img_view.move_items_by(2, 2)

def test_find_nice_position():
    from himena_builtins.qt.widgets._image_components._mouse_events import _find_nice_position, _find_nice_rect_position

    for angle in np.linspace(0, np.pi * 2, 30):
        x = float(np.sin(angle))
        y = float(np.cos(angle))
        p = _find_nice_position(QtCore.QPointF(x, y), QtCore.QPointF(0, 0))
        ang_out = np.arctan2(p.y(), p.x())
        assert np.rad2deg(ang_out) % 45 < 0.1
        assert abs(angle - ang_out) <= 22.5

        p = _find_nice_rect_position(QtCore.QPointF(x, y), QtCore.QPointF(0, 0))
        assert abs(p.x()) == abs(p.y())

def test_flat_roi_always_selected(qtbot: QtBot):
    view = QImageView()
    qtbot.addWidget(view)
    cur_roi = LineRoi(start=(2, 4), end=(5, 5))
    view.update_model(
        create_image_model(
        np.zeros((5, 10, 10)),
            axes=[
                ArrayAxis(name="t"),
                ArrayAxis(name="y"),
                ArrayAxis(name="x"),
            ],
            current_roi=cur_roi,
            rois=RoiListModel(
                items=[cur_roi], indices=np.array([[-1, -1]]), axis_names=["t"],
            ),
        )
    )
    assert view._img_view._current_roi_item is not None
    view._dims_slider.setValue((1,))
    assert view._img_view._current_roi_item is not None

def test_select_rois(himena_ui: MainWindow):
    model = create_image_model(
        np.zeros((4, 4, 10, 10)),
        axes=["t", "z", "y", "x"],
        rois=RoiListModel(
            items=[
                LineRoi(name="ROI-0", start=(1, 1), end=(4, 5)),
                PointRoi2D(name="ROI-1", x=1, y=5),
            ],
            indices=np.array([[0, 0], [0, 0]], dtype=np.int32),
        )
    )
    himena_ui.add_data_model(model)
    himena_ui.exec_action("builtins:select-image-rois", with_params={"selections": [0]})
    assert isinstance(lmodel := himena_ui.current_model.value, RoiListModel)
    assert len(lmodel) == 1
    assert lmodel.items[0].name == "ROI-0"

def test_handle_events(qtbot: QtBot):
    view = QImageView()
    qtbot.addWidget(view)
    handles = RoiSelectionHandles(view._img_view)
    # line
    line_roi = _rois.QLineRoi(0, 0, 5, 5)
    handles.connect_roi(line_roi)
    for h in handles._handles:
        h.moved_by_mouse.emit(QtCore.QPointF(1, 1), QtCore.QPointF(0, 0))
    line_roi.setLine(0, 0, 6, 6)
    # rect
    rect_roi = _rois.QRectangleRoi(0, 0, 5, 8)
    handles.connect_roi(rect_roi)
    for h in handles._handles:
        h.moved_by_mouse.emit(QtCore.QPointF(1, 1), QtCore.QPointF(0, 0))
    rect_roi.setRect(0, 0, 6, 9)
    # path
    path_roi = _rois.QPolygonRoi([0, 1, 3, 0], [3, 5, 5, 3])
    handles.connect_roi(path_roi)
    for h in handles._handles:
        h.moved_by_mouse.emit(QtCore.QPointF(1, 1), QtCore.QPointF(0, 0))
    # point
    point_roi = _rois.QPointRoi(0, 0)
    handles.connect_roi(point_roi)
    for h in handles._handles:
        h.moved_by_mouse.emit(QtCore.QPointF(1, 1), QtCore.QPointF(0, 0))
    point_roi.setPos(1, 1)
    # points
    points_roi = _rois.QPointsRoi([0, 1], [0, 1])
    handles.connect_roi(points_roi)
    for h in handles._handles:
        h.moved_by_mouse.emit(QtCore.QPointF(1, 1), QtCore.QPointF(0, 0))
    points_roi.setPos(1, 1)
    # rotated rect
    rotated_roi = _rois.QRotatedRectangleRoi(
        QtCore.QPointF(0, 0),
        QtCore.QPointF(10, 10),
        6,
    )
    handles.connect_roi(rotated_roi)
    for h in handles._handles:
        h.moved_by_mouse.emit(QtCore.QPointF(1, 1), QtCore.QPointF(0, 0))
