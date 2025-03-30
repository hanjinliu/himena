from __future__ import annotations

from himena.types import DragDataModel, WidgetDataModel

_DRAGGING_MODEL: DragDataModel | None = None


def drag(model: DragDataModel | WidgetDataModel) -> None:
    global _DRAGGING_MODEL

    if isinstance(model, WidgetDataModel):
        model = DragDataModel(getter=model, type=model.type)
    elif not isinstance(model, DragDataModel):
        raise TypeError("The model must be an instance of DragDataModel.")
    _DRAGGING_MODEL = model


def drop() -> DragDataModel | None:
    global _DRAGGING_MODEL

    model = _DRAGGING_MODEL
    _DRAGGING_MODEL = None
    return model


def is_dragging() -> bool:
    return _DRAGGING_MODEL is not None


def get_dragging_model() -> DragDataModel | None:
    return _DRAGGING_MODEL


def clear():
    global _DRAGGING_MODEL
    _DRAGGING_MODEL = None
