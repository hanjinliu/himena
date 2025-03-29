from __future__ import annotations


from magicgui.widgets.bases import ButtonWidget
from superqt import QToggleSwitch
from magicgui.backends._qtpy.widgets import QBaseButtonWidget


class ToggleSwitch(ButtonWidget):
    """A toggle switch widget behaves like a check box."""

    def __init__(self, **kwargs):
        super().__init__(
            widget_type=QBaseButtonWidget,
            backend_kwargs={"qwidg": QToggleSwitch},
            **kwargs,
        )
        self.native: QToggleSwitch
