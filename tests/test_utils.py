from himena.utils.misc import is_subtype
import pytest

@pytest.mark.parametrize(
    "input_type, super_type, expected",
    [
        ("text", "text", True),
        ("text.something", "text", True),
        ("text", "text.something", False),
        ("text.something", "text.something", True),
        ("text.something", "text.other", False),
        ("a.b.c.d", "a.b.c", True),
    ],
)
def test_is_subtype(input_type, super_type, expected):
    assert is_subtype(input_type, super_type) == expected
