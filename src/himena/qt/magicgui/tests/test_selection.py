from himena.qt.magicgui import SelectionEdit, SliderRangeGetter

def test_string_parsing():
    widget = SelectionEdit(value=((3, 6), (5, 10)))
    assert widget.value == ((3, 6), (5, 10))
    assert widget._line_edit.value == "3:6, 5:10"
    widget.value = (None, 3), (6, None)
    assert widget.value == ((None, 3), (6, None))
    assert widget._line_edit.value == ":3, 6:"
    widget.value = None
    assert widget.value is None

def test_slider_range_getter():
    def _getter() -> int:
        return _getter.value
    _getter.value = 1
    widget = SliderRangeGetter(getter=_getter)
    assert widget.get_value() == (None, None)
    widget._get_value_btn_min.clicked()
    assert widget.get_value() == (1, None)
    _getter.value = 4
    widget._get_value_btn_max.clicked()
    assert widget.get_value() == (1, 5)
    assert widget._value_min.value == "1"
    assert widget._value_max.value == "4"  # inclusive max
    widget.set_value((4, 8))
    assert widget.get_value() == (4, 8)
    assert widget._value_min.value == "4"
    assert widget._value_max.value == "7"
