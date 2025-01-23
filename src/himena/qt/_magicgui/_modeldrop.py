from __future__ import annotations
from typing import Any, TypeVar

from magicgui.widgets.bases import ValueWidget
from magicgui.types import Undefined
from magicgui.application import use_app
from magicgui.backends._qtpy.widgets import QBaseValueWidget
from himena.qt._qmodeldrop import QModelDrop, QModelDropList
from himena.types import WidgetDataModel
from himena.widgets import SubWindow

_W = TypeVar("_W")


class QMagicguiModelDrop(QBaseValueWidget):
    _qwidget: QModelDrop

    def __init__(self, **kwargs: Any) -> None:
        types = kwargs.get("types", None)
        layout = kwargs.get("layout", "horizontal")
        super().__init__(
            lambda parent: QModelDrop(types=types, layout=layout, parent=parent),
            "to_model",
            "set_model",
            "valueChanged",
            **kwargs,
        )


class QMagicguiSubWindowDrop(QBaseValueWidget):
    _qwidget: QModelDrop

    def __init__(self, **kwargs: Any) -> None:
        types = kwargs.get("types", None)
        layout = kwargs.get("layout", "horizontal")
        super().__init__(
            lambda parent: QModelDrop(types=types, layout=layout, parent=parent),
            "subwindow",
            "set_subwindow",
            "windowChanged",
            **kwargs,
        )


class QMagicguiModelDropList(QBaseValueWidget):
    _qwidget: QModelDropList

    def __init__(self, **kwargs: Any) -> None:
        types = kwargs.get("types", None)
        layout = kwargs.get("layout", "vertical")
        super().__init__(
            lambda parent: QModelDropList(types=types, layout=layout, parent=parent),
            "models",
            "set_models",
            "modelsChanged",
            **kwargs,
        )


class QMagicguiSubWindowDropList(QBaseValueWidget):
    _qwidget: QModelDropList

    def __init__(self, **kwargs: Any) -> None:
        types = kwargs.get("types", None)
        layout = kwargs.get("layout", "vertical")
        super().__init__(
            lambda parent: QModelDropList(types=types, layout=layout, parent=parent),
            "windows",
            "set_windows",
            "windowsChanged",
            **kwargs,
        )


class _ModelDropValueWidget(ValueWidget[_W]):
    def __init__(self, widget_type, value=Undefined, **kwargs):
        app = use_app()
        assert app.native

        if types := kwargs.pop("types", None):
            if isinstance(types, (list, tuple)):
                for t in types:
                    _assert_str(t)
            else:
                types = [_assert_str(types)]
        backend_kwargs = {"types": types}
        if layout := kwargs.pop("layout", None):
            backend_kwargs["layout"] = layout
        ValueWidget.__init__(
            self,
            value=value,
            widget_type=widget_type,
            backend_kwargs=backend_kwargs,
            **kwargs,
        )


class ModelDrop(_ModelDropValueWidget[WidgetDataModel]):
    def __init__(self, value=Undefined, **kwargs):
        super().__init__(QMagicguiModelDrop, value=value, **kwargs)

    def get_value(self) -> WidgetDataModel:
        out = super().get_value()
        if out is None and not self._nullable:
            raise ValueError(f"No model is specified to {self.label!r}.")
        return out


class SubWindowDrop(_ModelDropValueWidget[SubWindow]):
    def __init__(self, value=Undefined, **kwargs):
        super().__init__(QMagicguiSubWindowDrop, value=value, **kwargs)

    def get_value(self) -> SubWindow:
        out = super().get_value()
        if out is None and not self._nullable:
            raise ValueError(f"No model is specified to {self.label!r}.")
        return out


class ModelListDrop(_ModelDropValueWidget[list[WidgetDataModel]]):
    def __init__(self, value=Undefined, **kwargs):
        super().__init__(QMagicguiModelDropList, value=value, **kwargs)


class SubWindowListDrop(_ModelDropValueWidget[list[SubWindow]]):
    def __init__(self, value=Undefined, **kwargs):
        super().__init__(QMagicguiSubWindowDropList, value=value, **kwargs)


def _assert_str(t):
    if not isinstance(t, str):
        raise TypeError(f"types must be a str or a list of str, got {t}")
    return t
