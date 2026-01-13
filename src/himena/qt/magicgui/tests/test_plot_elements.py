from himena.qt.magicgui._plot_elements import AxisPropertyEdit, DictEdit

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

def test_dict_edit():
    """Test the DictEdit widget."""
    options = {
        "lim": {
            "options": {"min": 0, "max": 10},
            "annotation": tuple[float, float],
            "value": (2, 6)
        },
        "scale": {"choices": ["linear", "log"], "annotation": str},
        "label": {"annotation": str},
        "grid": {"annotation": bool},
    }
    value = {
        "lim": (2, 6),
        "scale": "linear",
        "label": "y",
        "grid": True,
    }
    widget = DictEdit(options=options, value=value)
    widget.value = {
        "lim": (1, 9),
        "scale": "log",
        "label": "Y-axis",
        "grid": False,
    }
    assert widget.value == {
        "lim": (1, 9),
        "scale": "log",
        "label": "Y-axis",
        "grid": False,
    }
