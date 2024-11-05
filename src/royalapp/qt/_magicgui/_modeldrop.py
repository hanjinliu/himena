from __future__ import annotations
from typing import Any

from magicgui.widgets.bases import ValueWidget
from magicgui.types import Undefined
from magicgui.application import use_app
from magicgui.backends._qtpy.widgets import QBaseValueWidget
from royalapp.qt._qmodeldrop import QModelDrop


class QMagicguiModelDrop(QBaseValueWidget):
    _qwidget: QModelDrop

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(QModelDrop, "value", "set_value", "valueChanged", **kwargs)


class ModelDrop(ValueWidget):
    def __init__(self, value=Undefined, **kwargs):
        app = use_app()
        assert app.native
        ValueWidget.__init__(
            self,
            value=value,
            widget_type=QMagicguiModelDrop,
            **kwargs,
        )
