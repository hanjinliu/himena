"""Widget wrappers."""

from __future__ import annotations

from typing import Generic, TYPE_CHECKING, TypeVar
import weakref

from psygnal import Signal
from royalapp.types import SubWindowState, WidgetDataModel, WindowRect

if TYPE_CHECKING:
    from royalapp.widgets import BackendMainWindow

_W = TypeVar("_W")  # backend widget type


class _HasMainWindowRef(Generic[_W]):
    def __init__(self, main_window: BackendMainWindow[_W]):
        self._main_window_ref = weakref.ref(main_window)

    def _main_window(self) -> BackendMainWindow[_W]:
        out = self._main_window_ref()
        if out is None:
            raise RuntimeError("Main window was deleted")
        return out


class WidgetWrapper(_HasMainWindowRef[_W]):
    def __init__(
        self,
        widget: _W,
        main_window: BackendMainWindow[_W],
        identifier: int | None = None,
    ):
        super().__init__(main_window)
        self._widget = weakref.ref(widget)
        widget._royalapp_widget = self
        if identifier is None:
            identifier = id(widget)
        self._identifier = identifier

    @property
    def widget(self) -> _W:
        """Get the internal backend widget."""
        if out := self._widget():
            return out
        raise RuntimeError("Widget was deleted.")


class SubWindow(WidgetWrapper[_W]):
    state_changed = Signal(SubWindowState)
    closed = Signal()

    def __repr__(self) -> str:
        return f"{type(self).__name__}(title={self.title!r}, widget={self.widget!r})"

    def __class_getitem__(cls, widget_type: type[_W]):
        # this hack allows in_n_out to assign both SubWindow and SubWindow[T] to the
        # same provider/processor.
        return cls

    @property
    def title(self) -> str:
        """Title of the sub-window."""
        return self._main_window()._window_title(self.widget)

    @title.setter
    def title(self, value: str) -> None:
        self._main_window()._set_window_title(self.widget, value)

    @property
    def state(self) -> SubWindowState:
        """State (e.g. maximized, minimized) of the sub-window."""
        return self._main_window()._window_state(self.widget)

    @state.setter
    def state(self, value: SubWindowState) -> None:
        self._main_window()._set_window_state(self.widget, value)

    @property
    def is_importable(self) -> bool:
        """Whether the widget accept importing values."""
        return hasattr(self.widget, "from_model") and isinstance(
            vars(type(self.widget))["from_model"], (classmethod, staticmethod)
        )

    @property
    def is_exportable(self) -> bool:
        """Whether the widget can export its data."""
        return hasattr(self.widget, "to_model")

    def to_model(self) -> WidgetDataModel:
        """Export the widget data."""
        if not self.is_exportable:
            raise ValueError("Widget does not have `to_model` method.")
        return self.widget.to_model()  # type: ignore

    @property
    def window_rect(self) -> WindowRect:
        """Position and size of the sub-window."""
        return self._main_window()._window_rect(self.widget)

    @window_rect.setter
    def window_rect(self, value) -> None:
        self._main_window()._set_window_rect(
            self.widget, WindowRect.from_numbers(*value)
        )


class DockWidget(WidgetWrapper[_W]):
    @property
    def visible(self) -> bool:
        """Visibility of the dock widget."""
        return self._main_window()._dock_widget_visible(self.widget)

    @visible.setter
    def visible(self, visible: bool) -> bool:
        return self._main_window()._set_dock_widget_visible(self.widget, visible)

    def show(self) -> None:
        """Show the dock widget."""
        self.visible = True

    def hide(self) -> None:
        """Hide the dock widget."""
        self.visible = False

    @property
    def title(self) -> str:
        """Title of the dock widget."""
        return self._main_window()._dock_widget_title(self.widget)

    @title.setter
    def title(self, title: str) -> None:
        return self._main_window()._set_dock_widget_title(self.widget, str(title))
