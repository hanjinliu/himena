from __future__ import annotations
from typing import Any, TYPE_CHECKING

from qtpy import QtWidgets as QtW, QtCore
from magicgui.types import Undefined
from magicgui.widgets.bases import CategoricalWidget
from magicgui.widgets.bases._mixins import _OrientationMixin
from magicgui.backends._qtpy.widgets import (
    RadioButtons as _RadioButtons,
    QBaseValueWidget,
)

if TYPE_CHECKING:
    from typing import Unpack
    from magicgui.types import ChoicesType
    from magicgui.widgets.bases._widget import WidgetKwargs


class QCheckableButton(QtW.QPushButton):
    def __init__(self, label: str, parent: QtW.QWidget | None = None):
        super().__init__(label, parent)
        self.setCheckable(True)
        self.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)


class _ToggleButtons(_RadioButtons):
    _qwidget: QtW.QWidget

    def __init__(self, **kwargs: Any) -> None:
        QBaseValueWidget.__init__(self, QtW.QWidget, "", "", "", **kwargs)
        self._btn_group = QtW.QButtonGroup(self._qwidget)
        self._mgui_set_orientation("horizontal")
        self._btn_group.buttonToggled.connect(self._emit_data)

    def _add_button(self, label: str, data: Any | None = None):
        btn = QCheckableButton(label, self._qwidget)
        btn.setCheckable(True)
        btn._data = data
        self._btn_group.addButton(btn)
        self._qwidget.layout().addWidget(btn)


class ToggleButtons(CategoricalWidget, _OrientationMixin):
    def __init__(
        self,
        choices: ChoicesType = (),
        orientation: str = "horizontal",
        **kwargs: Unpack[WidgetKwargs],
    ) -> None:
        kwargs["widget_type"] = _ToggleButtons
        super().__init__(choices=choices, **kwargs)
        self.orientation = orientation
        if (
            kwargs.get("value", Undefined) is Undefined
            and choices
            and not self._nullable
        ):
            self.value = self.choices[0]
