from __future__ import annotations

import inspect
import weakref
from himena.types import WidgetDataModel, WindowState, WindowRect


class MockWidget:
    def __init__(self) -> None:
        self._subwindow_ref = lambda: None
        self._dockwidget_ref = lambda: None

    @property
    def subwindow(self) -> MockSubWindow:
        if win := self._subwindow_ref():
            return win
        raise ValueError("Subwindow not set")

    @property
    def dockwidget(self) -> MockDockWidget:
        if dock := self._dockwidget_ref():
            return dock
        raise ValueError("Dockwidget not set")

    def set_subwindow(self, subwindow: MockSubWindow) -> None:
        """Set the subwindow reference."""
        self._subwindow_ref = weakref.ref(subwindow)

    def set_dockwidget(self, dockwidget: MockDockWidget) -> None:
        """Set the dockwidget reference."""
        self._dockwidget_ref = weakref.ref(dockwidget)


class MockSubWindow:
    def __init__(self, widget: MockWidget, parent: MockTab, title: str = ""):
        self._widget = widget
        self._parent = weakref.ref(parent)
        self._state = WindowState.NORMAL
        self._rect = WindowRect(0, 0, 800, 600)
        self._title = title

    @property
    def tab(self) -> MockTab:
        return self._parent()


class MockTab:
    def __init__(self, title: str = ""):
        self.sub_windows: list[MockSubWindow] = []
        self.current_index: int | None = None
        self.title = title

    def __getitem__(self, index: int) -> MockSubWindow:
        return self.sub_windows[index]


class MockDockWidget:
    def __init__(self, widget: MockWidget, title: str = ""):
        self._widget = widget
        self.title = title
        self._visible = True


class MockParametricWidget(MockWidget):
    def __init__(self, sig: inspect.Signature):
        super().__init__()
        self._sig = sig

    def get_params(self):
        out = {}
        for param in self._sig.parameters.values():
            if param.default == inspect.Parameter.empty:
                raise ValueError(f"Parameter {param.name} has no default value")
            out[param.name] = param.default
        return out

    def connect_changed_signal(self, callback):
        """Do nothing."""

    def is_preview_enabled(self):
        return False


class MockModelWrapper(MockWidget):
    def __init__(self):
        super().__init__()
        self._model: WidgetDataModel | None = None

    def update_model(self, model: WidgetDataModel) -> None:
        self._model = model

    def to_model(self) -> WidgetDataModel:
        if self._model is None:
            raise ValueError("Model not set")
        return self._model.model_copy()
