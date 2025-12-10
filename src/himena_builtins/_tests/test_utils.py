from qtpy import QtWidgets as QtW
import numpy as np
from himena_builtins.qt.widgets._shared import index_contains, labeled, quick_min_max
from himena_builtins.qt.plot._conversion import _parse_styled_text
from himena.standards.plotting import StyledText

def test_quick_min_max():
    arr = np.arange(1234567)
    quick_min_max(arr, down_sample_to=100000)
    arr_bool = np.array([False, True])
    assert quick_min_max(arr_bool) == (0.0, 1.0)

def test_labeled_widget(qtbot):
    labeled_widget = labeled("Label:", QtW.QPushButton("Button"), QtW.QLineEdit())
    qtbot.addWidget(labeled_widget)

def test_index_contains():
    assert index_contains(3, 3)
    assert not index_contains(3, 4)
    assert index_contains(slice(2, 5), 3)
    assert not index_contains(slice(2, 5), 5)
    arr = np.array([1, 2, 3])
    assert index_contains(arr, 2)
    assert not index_contains(arr, 4)

def test_parse_styled_text():
    _parse_styled_text(StyledText(text="abc"))
    _parse_styled_text(
        StyledText(text="abc", size=10, color="blue", family="sans-serif", bold=True, italic=True, underline=True, alignment="center")
    )
    _parse_styled_text("abc")
