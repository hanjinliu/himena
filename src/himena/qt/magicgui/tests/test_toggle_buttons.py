from himena.qt.magicgui._toggle_buttons import ToggleButtons

def test_toggle_buttons():
    btns = ToggleButtons(choices=["A", "B", "C"], orientation="vertical")
    assert btns.value == "A"
    btns.value = "B"
    assert btns.value == "B"

    btns.choices = ["X", "Y", "Z"]
    assert btns.value == "X"
