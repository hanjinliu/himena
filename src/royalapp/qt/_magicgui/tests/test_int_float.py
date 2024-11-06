import pytest
from royalapp.qt._magicgui._basic_widgets import float_to_str

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
