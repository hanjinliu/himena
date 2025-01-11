from __future__ import annotations
from typing import Any, Generic, TypeVar, overload

from himena.plugins import _checker
from himena.types import DragDataModel, DropResult, Size, WidgetDataModel
from himena.style.core import get_global_styles

_W = TypeVar("_W")


class WidgetTester(Generic[_W]):
    def __init__(self, widget: _W):
        self._widget = widget

    def __enter__(self) -> WidgetTester[_W]:
        _checker.call_theme_changed_callback(
            self._widget, get_global_styles()["light-green"]
        )
        _checker.call_widget_activated_callback(self._widget)
        _checker.call_widget_added_callback(self._widget)
        if hasattr(self._widget, "control_widget"):
            self._widget.control_widget()
        if hasattr(self._widget, "size_hint"):
            hint = self._widget.size_hint()
            _checker.call_widget_resized_callback(
                self._widget, Size(200, 200), Size(*hint)
            )
        if hasattr(self._widget, "is_editable"):
            self._widget.is_editable()
        if hasattr(self._widget, "set_editable"):
            self._widget.set_editable(False)
            self._widget.set_editable(True)
        return self

    def __exit__(self, *args):
        if hasattr(self._widget, "is_modified"):
            self._widget.is_modified()
        _checker.call_widget_closed_callback(self._widget)

    @overload
    def update_model(self, model: WidgetDataModel) -> WidgetTester[_W]: ...
    @overload
    def update_model(
        self,
        *,
        value: Any,
        type: str | None = None,
        metadata: Any | None = None,
        **kwargs,
    ) -> WidgetTester[_W]: ...

    def update_model(
        self, model: WidgetDataModel | None = None, **kwargs
    ) -> WidgetTester[_W]:
        model = self._norm_model_input(model, **kwargs)
        self._widget.update_model(model)
        return self

    def to_model(self) -> WidgetDataModel:
        return self._widget.to_model()

    def cycle_model(self) -> tuple[WidgetDataModel, WidgetDataModel]:
        """Cycle `update_model` and `to_model` and return both."""
        model = self.to_model()
        self.update_model(model)
        return model, self.to_model()

    @overload
    def drop_model(self, model: WidgetDataModel) -> DropResult: ...
    @overload
    def drop_model(
        self,
        *,
        value: Any,
        type: str | None = None,
        metadata: Any | None = None,
        **kwargs,
    ) -> DropResult: ...

    def drop_model(self, model: WidgetDataModel | None = None, **kwargs):
        model = self._norm_model_input(model, **kwargs)
        drag_data_model = DragDataModel(getter=model, type=model.type)
        if not drag_data_model.widget_accepts_me(self.widget):
            raise ValueError(
                f"Widget {self.widget!r} does not accept dropping {model.type}"
            )
        return self.widget.dropped_callback(model)

    def is_modified(self) -> bool:
        return self._widget.is_modified()

    @property
    def widget(self) -> _W:
        return self._widget

    def _norm_model_input(self, model, **kwargs) -> WidgetDataModel:
        if model:
            if kwargs:
                raise TypeError("Cannot specify both model and kwargs")
            return model
        else:
            if kwargs.get("type") is None:
                try:
                    kwargs["type"] = self._widget.model_type()
                except AttributeError:
                    raise TypeError("`type` argument must be specified") from None
            return WidgetDataModel(**kwargs)
