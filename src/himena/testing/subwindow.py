from __future__ import annotations
from typing import Generic, TypeVar

from himena.plugins import _checker
from himena.types import Size, WidgetDataModel

_W = TypeVar("_W")


class WidgetTester(Generic[_W]):
    def __init__(self, widget: _W):
        self._widget = widget

    def test_callbacks(self):
        _checker.call_theme_changed_callback(self._widget)
        _checker.call_widget_activated_callback(self._widget)
        _checker.call_widget_added_callback(self._widget)
        _checker.call_widget_resized_callback(
            self._widget, Size(200, 200), Size(240, 240)
        )
        _checker.call_widget_resized_callback(
            self._widget, Size(240, 240), Size(200, 200)
        )
        _checker.call_widget_closed_callback(self._widget)

    def update_model(self, model: WidgetDataModel) -> WidgetTester[_W]:
        self._widget.update_model(model)
        return self

    def to_model(self) -> WidgetDataModel:
        return self._widget.to_model()
