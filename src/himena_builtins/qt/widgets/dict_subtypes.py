from __future__ import annotations

import numpy as np

from himena_builtins.qt.widgets.array import QArrayView, QArrayViewControl
from himena_builtins.qt.widgets.dataframe import QDataFrameView, QDataFrameViewControl
from himena_builtins.qt.widgets.dict import QDictOfWidgetEdit, QTabControl
from himena import MainWindow
from himena.types import WidgetDataModel
from himena.consts import StandardType
from himena.plugins import validate_protocol


class QDataFrameStack(QDictOfWidgetEdit):
    """DataFrame Stack widget."""

    __himena_widget_id__ = "builtins:QDataFrameStack"
    __himena_display_name__ = "Built-in DataFrame Stack"

    def __init__(self, ui: MainWindow):
        super().__init__()
        self._ui = ui
        self._model_type_component = StandardType.DATAFRAME
        self._model_type = StandardType.DATAFRAMES
        self._control = QDataFramesControl()

    def _default_widget(self) -> QDataFrameView:
        table = QDataFrameView(self._ui)
        table.update_model(WidgetDataModel(value={}, type=StandardType.DATAFRAME))
        return table

    @validate_protocol
    def control_widget(self) -> QDataFramesControl:
        return self._control


class QDataFramesControl(QDataFrameViewControl, QTabControl):
    def update_for_component(self, widget):
        return self.update_for_table(widget)


class QArrayStack(QDictOfWidgetEdit):
    __himena_widget_id__ = "builtins:QArrayStack"
    __himena_display_name__ = "Built-in Array Stack"

    def __init__(self, ui: MainWindow):
        super().__init__()
        self._ui = ui
        self._model_type_component = StandardType.ARRAY
        self._model_type = StandardType.ARRAYS
        self._control = QArrayStackControl()

    def _default_widget(self) -> QArrayView:
        view = QArrayView(self._ui)
        view.update_model(
            WidgetDataModel(value=np.zeros((0, 0)), type=StandardType.ARRAY)
        )
        return view

    @validate_protocol
    def control_widget(self) -> QArrayStackControl:
        return self._control


class QArrayStackControl(QArrayViewControl, QTabControl):
    def update_for_component(self, widget: QArrayView):
        return self.update_for_array(widget)
