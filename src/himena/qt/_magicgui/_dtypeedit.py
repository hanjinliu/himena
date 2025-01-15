from __future__ import annotations

import numpy as np
from magicgui.widgets.bases import ValueWidget
from magicgui.types import Undefined
from magicgui.application import use_app
from magicgui.backends._qtpy.widgets import QBaseValueWidget
from himena.qt._qdtypeedit import QNumericDTypeEdit


class QBaseNumericDTypeEdit(QBaseValueWidget):
    def __init__(self, **kwargs) -> None:
        super().__init__(
            QNumericDTypeEdit, "dtype", "set_dtype", "valueChanged", **kwargs
        )


class NumericDTypeEdit(ValueWidget[str]):
    def __init__(self, value=Undefined, **kwargs):
        app = use_app()
        assert app.native
        if value is Undefined:
            value = "float64"
        elif isinstance(value, np.dtype):
            value = str(value)
        ValueWidget.__init__(
            self,
            value=value,
            widget_type=QBaseNumericDTypeEdit,
            **kwargs,
        )
