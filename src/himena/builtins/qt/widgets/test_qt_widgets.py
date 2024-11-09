import numpy as np
from qtpy.QtCore import Qt
from himena.builtins.qt.widgets import (
    QDefaultTextEdit,
    QDefaultTableWidget,
    QDefaultImageView,
)
from himena import WidgetDataModel
from pytestqt.qtbot import QtBot

_Ctrl = Qt.KeyboardModifier.ControlModifier


def test_text_edit(qtbot: QtBot):
    model = WidgetDataModel(value="a\nb", type="text")
    text_edit = QDefaultTextEdit.from_model(model)
    qtbot.addWidget(text_edit)
    main = text_edit._main_text_edit

    assert text_edit.to_model().value == "a\nb"
    assert text_edit.toPlainText() == "a\nb"
    # move to the end
    qtbot.keyClick(main, Qt.Key.Key_End, modifier=_Ctrl)
    qtbot.keyClick(main, Qt.Key.Key_Down)
    qtbot.keyClick(main, Qt.Key.Key_End, modifier=_Ctrl)
    qtbot.keyClick(main, Qt.Key.Key_Down)
    qtbot.keyClick(main, Qt.Key.Key_End, modifier=_Ctrl)

    qtbot.keyClick(main, Qt.Key.Key_Return)
    qtbot.keyClick(main, Qt.Key.Key_Tab)
    qtbot.keyClick(main, Qt.Key.Key_Backtab)
    qtbot.keyClick(main, Qt.Key.Key_Tab)
    qtbot.keyClick(main, Qt.Key.Key_O)
    qtbot.keyClick(main, Qt.Key.Key_P)
    assert text_edit.to_model().value.splitlines() == ["a", "b", "    op"]
    qtbot.keyClick(main, Qt.Key.Key_Home)
    qtbot.keyClick(main, Qt.Key.Key_Up, modifier=Qt.KeyboardModifier.AltModifier)
    qtbot.keyClick(main, Qt.Key.Key_Down, modifier=Qt.KeyboardModifier.AltModifier)
    qtbot.keyClick(main, Qt.Key.Key_Down)
    qtbot.keyClick(main, Qt.Key.Key_Down)
    qtbot.keyClick(main, Qt.Key.Key_Down)
    qtbot.keyClick(main, Qt.Key.Key_Tab)
    qtbot.keyClick(main, Qt.Key.Key_X)
    qtbot.keyClick(main, Qt.Key.Key_Return)
    qtbot.keyClick(main, Qt.Key.Key_A)
    qtbot.keyClick(main, Qt.Key.Key_B)
    qtbot.keyClick(main, Qt.Key.Key_C)
    qtbot.keyClick(main, Qt.Key.Key_D)
    qtbot.keyClick(main, Qt.Key.Key_L, modifier=_Ctrl)
    qtbot.keyClick(main, Qt.Key.Key_Up, modifier=Qt.KeyboardModifier.AltModifier)
    qtbot.keyClick(main, Qt.Key.Key_Down, modifier=Qt.KeyboardModifier.AltModifier)
    qtbot.keyClick(main, Qt.Key.Key_Left)
    qtbot.keyClick(main, Qt.Key.Key_D, modifier=_Ctrl)
    qtbot.keyClick(main, Qt.Key.Key_C, modifier=_Ctrl)
    qtbot.keyClick(main, Qt.Key.Key_Return)
    qtbot.keyClick(main, Qt.Key.Key_V, modifier=_Ctrl)
    qtbot.keyClick(main, Qt.Key.Key_Less, modifier=_Ctrl)
    qtbot.keyClick(main, Qt.Key.Key_Greater, modifier=_Ctrl)
    qtbot.keyClick(main, Qt.Key.Key_Greater, modifier=_Ctrl)
    qtbot.keyClick(main, Qt.Key.Key_0, modifier=_Ctrl)
    qtbot.keyClick(text_edit, Qt.Key.Key_F, modifier=_Ctrl)
    text_edit.resize(100, 100)
    text_edit.resize(120, 120)


def test_table_edit(qtbot: QtBot):
    model = WidgetDataModel(value=[["a", "b"], [0, 1]], type="table")
    table_widget = QDefaultTableWidget.from_model(model)
    qtbot.addWidget(table_widget)
    qtbot.keyClick(table_widget, Qt.Key.Key_A, modifier=_Ctrl)
    qtbot.keyClick(table_widget, Qt.Key.Key_C, modifier=_Ctrl)
    qtbot.keyClick(table_widget, Qt.Key.Key_X, modifier=_Ctrl)
    qtbot.keyClick(table_widget, Qt.Key.Key_V, modifier=_Ctrl)
    qtbot.keyClick(table_widget, Qt.Key.Key_Delete)
    qtbot.keyClick(table_widget, Qt.Key.Key_F, modifier=_Ctrl)
    table_widget.resize(100, 100)
    qtbot


def test_image_view(qtbot: QtBot):
    # grayscale
    model = WidgetDataModel(
        value=np.arange(100, dtype=np.uint8).reshape(10, 10), type="image"
    )
    image_view = QDefaultImageView.from_model(model)
    assert len(image_view._sliders) == 0

    # RGB
    model = WidgetDataModel(
        value=np.zeros((100, 100, 3), dtype=np.uint16), type="image"
    )
    image_view = QDefaultImageView.from_model(model)
    assert len(image_view._sliders) == 0
    image_view._interpolation_check_box.setChecked(False)
    image_view._interpolation_check_box.setChecked(True)

    # 5D
    rng = np.random.default_rng(14442)
    model = WidgetDataModel(
        value=rng.random((10, 5, 3, 100, 100), dtype=np.float32), type="image"
    )
    image_view = QDefaultImageView.from_model(model)
