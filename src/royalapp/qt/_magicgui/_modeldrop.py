from __future__ import annotations
from typing import Any, Hashable

from magicgui.widgets.bases import ValueWidget
from magicgui.types import Undefined
from magicgui.application import use_app
from magicgui.backends._qtpy.widgets import QBaseValueWidget
from royalapp.qt._qmodeldrop import QModelDrop


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


class ModelDrop(ValueWidget):
    def __init__(self, value=Undefined, **kwargs):
        app = use_app()
        assert app.native

        if types := kwargs.pop("types", None):
            if isinstance(types, list):
                for t in types:
                    _assert_hashable(t)
            else:
                types = [_assert_hashable(types)]
        ValueWidget.__init__(
            self,
            value=value,
            widget_type=QMagicguiModelDrop,
            backend_kwargs={"types": types},
            **kwargs,
        )


def _assert_hashable(t):
    if not isinstance(t, Hashable):
        raise TypeError(f"types must be a Hashable or a list of Hashables, got {t}")
    return t
