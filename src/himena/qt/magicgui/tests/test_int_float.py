import pytest
from himena.qt.magicgui._basic_widgets import float_to_str, IntEdit, FloatEdit, IntListEdit, FloatListEdit

@pytest.mark.parametrize(
    "value, expected",
    [
        (1.0, "1.0"),
        (14, "14"),
        (0.024, "0.024"),
        (0.046999999998, "0.047"),
        (1.32e8, "1.32e+08"),
        (0.00005335, "5.335e-05"),
        (199000000, "1.99e+08"),
    ]
)
def test_float_to_str(value, expected: str):
    assert float_to_str(value) == expected

def test_properties_int_widget():
    edit = IntEdit(value=2)
    assert edit.native.placeholderText() == "required"
    assert edit.value == 2
    assert edit.min < -100000
    assert edit.max > 100000
    edit = IntEdit(value=-4, min=-6, max=10)
    assert edit.value == -4
    assert edit.min == -6
    assert edit.max == 10
    with pytest.raises(ValueError):
        edit.value = None
    edit = IntEdit(min=-6, max=10, nullable=True)
    assert edit.value is None
    edit.value = 3
    assert edit.value == 3
    edit.value = None
    assert edit.value is None
    assert edit.native.placeholderText() == ""

def test_properties_float_widget():
    edit = FloatEdit(value=2.5)
    assert edit.native.placeholderText() == "required"
    assert edit.value == pytest.approx(2.5)
    assert edit.min < -1e10
    assert edit.max > 1e10
    edit = FloatEdit(value=-4.2, min=-6.5, max=10.1)
    assert edit.value == pytest.approx(-4.2)
    assert edit.min == pytest.approx(-6.5)
    assert edit.max == pytest.approx(10.1)
    with pytest.raises(ValueError):
        edit.value = None
    edit = FloatEdit(min=-6.5, max=10.1, nullable=True)
    assert edit.value is None
    edit.value = 3.14
    assert edit.value == pytest.approx(3.14)
    edit.value = None
    assert edit.value is None
    assert edit.native.placeholderText() == ""

def test_properties_list_widget():
    edit = IntListEdit(value=[1, 2, 3])
    assert edit.value == [1, 2, 3]
    assert edit.native.text() == "1, 2, 3"
    edit.value = [10, 20]
    assert edit.value == [10, 20]
    assert edit.native.text() == "10, 20"
    edit = IntListEdit()
    assert edit.value == []
    with pytest.raises(ValueError):
        edit.value = None
    edit = IntListEdit(value=[1, 2, 3], nullable=True)
    edit.value = None
    assert not edit.value
    assert edit.native.text() == ""

    edit = FloatListEdit(value=[1.5, 2.5, 3.5])
    assert edit.value == pytest.approx([1.5, 2.5, 3.5])
    assert edit.native.text() == "1.5, 2.5, 3.5"
    edit.value = [10.1, 20.2]
    assert edit.value == pytest.approx([10.1, 20.2])
    assert edit.native.text() == "10.1, 20.2"
    with pytest.raises(ValueError):
        edit.value = None
    edit = FloatListEdit(value=[1.5, 2.1, 3.1], nullable=True)
    edit.value = None
    assert not edit.value
    assert edit.native.text() == ""
