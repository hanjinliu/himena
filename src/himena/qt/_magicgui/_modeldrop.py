from __future__ import annotations
from typing import Any

from magicgui.widgets.bases import ValueWidget
from magicgui.types import Undefined
from magicgui.application import use_app
from magicgui.backends._qtpy.widgets import QBaseValueWidget
from himena.qt._qmodeldrop import QModelDrop
from himena.types import WidgetDataModel


class QMagicguiModelDrop(QBaseValueWidget):
    _qwidget: QModelDrop

    def __init__(self, **kwargs: Any) -> None:
        types = kwargs.get("types", None)
        super().__init__(
            lambda parent: QModelDrop(types=types, parent=parent),
            "value",
            "set_value",
            "valueChanged",
            **kwargs,
        )


class ModelDrop(ValueWidget[WidgetDataModel]):
    def __init__(self, value=Undefined, **kwargs):
        app = use_app()
        assert app.native

        if types := kwargs.pop("types", None):
            if isinstance(types, (list, tuple)):
                for t in types:
                    _assert_str(t)
            else:
                types = [_assert_str(types)]
        ValueWidget.__init__(
            self,
            value=value,
            widget_type=QMagicguiModelDrop,
            backend_kwargs={"types": types},
            **kwargs,
        )

    def get_value(self) -> WidgetDataModel:
        out = super().get_value()
        if out is None and not self._nullable:
            raise ValueError(f"No model is specified to {self.label!r}.")
        return out


def _assert_str(t):
    if not isinstance(t, str):
        raise TypeError(f"types must be a str or a list of str, got {t}")
    return t
