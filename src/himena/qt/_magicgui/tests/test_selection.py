from himena.qt._magicgui._selection import SelectionEdit

def test_string_parsing():
    widget = SelectionEdit(value=((3, 6), (5, 10)))
    assert widget.value == ((3, 6), (5, 10))
    assert widget._line_edit.value == "3:6, 5:10"
    widget.value = (None, 3), (6, None)
    assert widget.value == ((None, 3), (6, None))
    assert widget._line_edit.value == ":3, 6:"
    widget.value = None
    assert widget.value is None
