"""Widget wrappers."""

from __future__ import annotations

from pathlib import Path
from typing import Generic, TYPE_CHECKING, TypeVar
from uuid import uuid4
import weakref

from psygnal import Signal
from royalapp import anchor as _anchor
from royalapp.types import BackendInstructions, WindowState, WidgetDataModel, WindowRect
from royalapp._descriptors import (
    SaveBehavior,
    SaveToNewPath,
    SaveToPath,
    MethodDescriptor,
    ProgramaticMethod,
)

if TYPE_CHECKING:
    from royalapp.widgets import BackendMainWindow, MainWindow

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
            identifier = uuid4().int
        self._identifier = identifier
        self._save_behavior: SaveBehavior = SaveToNewPath()
        self._widget_data_model_method: MethodDescriptor = ProgramaticMethod()

    @property
    def widget(self) -> _W:
        """Get the internal backend widget."""
        if out := self._widget():
            return out
        raise RuntimeError("Widget was deleted.")

    @property
    def save_behavior(self) -> SaveBehavior:
        """Get the save behavior of the widget."""
        return self._save_behavior

    def update_default_save_path(self, path: str | Path) -> None:
        """Update the save behavior of the widget."""
        self._save_behavior = SaveToPath(path=Path(path), ask_overwrite=True)
        if hasattr(self.widget, "set_modified"):
            self.widget.set_modified(False)
        return None

    def _update_widget_data_model_method(self, method: MethodDescriptor) -> None:
        """Update the method descriptor of the widget."""
        self._widget_data_model_method = method
        return None


class SubWindow(WidgetWrapper[_W]):
    state_changed = Signal(WindowState)
    renamed = Signal(str)
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
    def state(self) -> WindowState:
        """State (e.g. maximized, minimized) of the sub-window."""
        return self._main_window()._window_state(self.widget)

    @state.setter
    def state(self, value: WindowState) -> None:
        inst = self._main_window()._royalapp_main_window._instructions
        self._main_window()._set_window_state(self.widget, value, inst)

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

    @property
    def is_modified(self) -> bool:
        """Whether the content of the widget has been modified."""
        is_modified_func = getattr(self.widget, "is_modified", None)
        return callable(is_modified_func) and is_modified_func()

    def size_hint(self) -> tuple[int, int] | None:
        """Size hint of the sub-window."""
        return getattr(self.widget, "size_hint", lambda: None)()

    def model_type(self) -> str | None:
        """Type of the widget data model."""
        return getattr(self.widget, "model_type", lambda: None)()

    def to_model(self) -> WidgetDataModel:
        """Export the widget data."""
        if not self.is_exportable:
            raise ValueError("Widget does not have `to_model` method.")
        model = self.widget.to_model()  # type: ignore
        if not isinstance(model, WidgetDataModel):
            raise TypeError(
                "`to_model` method must return an instance of WidgetDataModel, got "
                f"{type(model)}"
            )
        # TODO: check the model type
        if model.title is None:
            model.title = self.title
        if model.method is None:
            model.method = self._widget_data_model_method
        return model

    @property
    def rect(self) -> WindowRect:
        """Position and size of the sub-window."""
        return self._main_window()._window_rect(self.widget)

    @rect.setter
    def rect(self, value: tuple[int, int, int, int]) -> None:
        main = self._main_window()._royalapp_main_window
        inst = main._instructions.updated(animate=False)
        self._set_rect(value, inst)

    def _set_rect(
        self,
        value: tuple[int, int, int, int],
        inst: BackendInstructions | None = None,
    ):
        if self.state is not WindowState.NORMAL:
            raise ValueError(
                "Cannot set window rect when window is not in normal state."
            )
        if inst is None:
            inst = self._main_window()._royalapp_main_window._instructions
        main = self._main_window()
        rect = WindowRect.from_numbers(*value)
        anc = main._window_anchor(self.widget).update_for_window_rect(
            main._area_size(), rect
        )
        main._set_window_rect(self.widget, rect, inst)
        main._set_window_anchor(self.widget, anc)

    @property
    def anchor(self) -> _anchor.WindowAnchor:
        """Anchor of the sub-window."""
        return self._main_window()._window_anchor(self.widget)

    @anchor.setter
    def anchor(self, anchor: _anchor.WindowAnchor | None):
        if anchor is None:
            anchor = _anchor.NoAnchor
        elif isinstance(anchor, str):
            anchor = self._anchor_from_str(anchor)
        elif not isinstance(anchor, _anchor.WindowAnchor):
            raise TypeError(f"Expected WindowAnchor, got {type(anchor)}")
        self._main_window()._set_window_anchor(self.widget, anchor)

    def update(
        self,
        *,
        rect: tuple[int, int, int, int] | None = None,
        state: WindowState | None = None,
        title: str | None = None,
        anchor: _anchor.WindowAnchor | str | None = None,
    ) -> SubWindow[_W]:
        if rect is not None:
            self.rect = rect
        if state is not None:
            self.state = state
        if title is not None:
            self.title = title
        if anchor is not None:
            self.anchor = anchor
        return self

    def _anchor_from_str(sub_win: SubWindow[_W], anchor: str):
        rect = sub_win.rect
        w0, h0 = sub_win._main_window()._area_size()
        if anchor in ("top-left", "top left", "top_left"):
            return _anchor.TopLeftConstAnchor(rect.left, rect.top)
        elif anchor in ("top-right", "top right", "top_right"):
            return _anchor.TopRightConstAnchor(w0 - rect.right, rect.top)
        elif anchor in ("bottom-left", "bottom left", "bottom_left"):
            return _anchor.BottomLeftConstAnchor(rect.left, h0 - rect.bottom)
        elif anchor in ("bottom-right", "bottom right", "bottom_right"):
            return _anchor.BottomRightConstAnchor(w0 - rect.right, h0 - rect.bottom)
        else:
            raise ValueError(f"Unknown anchor: {anchor}")

    def _find_me(self, main: MainWindow) -> tuple[int, int]:
        for i_tab, tab in enumerate(main.tabs):
            for i_win, win in enumerate(tab):
                if win is self:
                    return i_tab, i_win
        raise RuntimeError(f"SubWindow {self.title} not found in main window.")

    def _close_me(self, main: MainWindow, confirm: bool = False) -> None:
        if (
            self.is_modified
            and confirm
            and not main.exec_confirmation_dialog(f"Close {self.title} without saving?")
        ):
            return None
        i_tab, i_win = self._find_me(main)
        del main.tabs[i_tab][i_win]


class DockWidget(WidgetWrapper[_W]):
    def __repr__(self) -> str:
        return f"{type(self).__name__}(title={self.title!r}, widget={self.widget!r})"

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
