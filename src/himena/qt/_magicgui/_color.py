from __future__ import annotations
from typing import Any

from magicgui.widgets.bases import ValueWidget
from magicgui.types import Undefined
from magicgui.application import use_app
from magicgui.backends._qtpy.widgets import QBaseValueWidget
from cmap import Color, Colormap
from superqt import QColormapComboBox
from himena._utils import lru_cache
from himena.qt._qcoloredit import QColorEdit


class _QColorEdit(QBaseValueWidget):
    _qwidget: QColorEdit

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(
            QColorEdit,
            "rgba",
            "setRgba",
            "colorChanged",
            **kwargs,
        )

    def _pre_set_hook(self, value: Any) -> Any:
        return Color(value)

    def _post_get_hook(self, value: Any) -> Any:
        return Color(value)


class ColorEdit(ValueWidget[Color]):
    def __init__(self, value=Undefined, **kwargs):
        app = use_app()
        assert app.native

        ValueWidget.__init__(
            self,
            value=value,
            widget_type=_QColorEdit,
            **kwargs,
        )


@lru_cache
def get_colormaps(category: str = "qualitative") -> list[str]:
    cat = Colormap.catalog()
    return sorted(cat.unique_keys(categories=[category]))


class _ColormapEdit(QBaseValueWidget):
    _qwidget: QColormapComboBox

    def __init__(self, **kwargs: Any) -> None:
        cat = kwargs.get("category", "qualitative")
        super().__init__(
            QColormapComboBox,
            "currentColormap",
            "setCurrentColormap",
            "currentColormapChanged",
            **kwargs,
        )
        self._qwidget.addColormaps(get_colormaps(cat))
        self._qwidget.setMinimumHeight(22)

    def _pre_set_hook(self, value: Any) -> Any:
        return Colormap(value)

    def _post_get_hook(self, value: Any) -> Any:
        return Colormap(value)


class ColormapEdit(ValueWidget[Colormap]):
    def __init__(self, value=Undefined, **kwargs):
        app = use_app()
        assert app.native

        if category := kwargs.pop("category", None):
            backend_kwargs = {"category": category}
        else:
            backend_kwargs = {}
        ValueWidget.__init__(
            self,
            value=value,
            widget_type=_ColormapEdit,
            backend_kwargs=backend_kwargs,
            **kwargs,
        )
