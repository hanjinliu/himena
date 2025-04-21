from himena.qt.magicgui._plot_elements import AxisPropertyEdit

def test_axis_property_edit():
    """Test the AxisPropertyEdit widget."""
    widget = AxisPropertyEdit()
    widget.value
    widget.value = {
        "lim": (2, 5),
        "scale": "linear",
        "label": "X-axis",
        "grid": True,
    }
