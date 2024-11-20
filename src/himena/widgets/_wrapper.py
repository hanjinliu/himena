"""Widget wrappers."""

from __future__ import annotations

from contextlib import suppress
import logging
from pathlib import Path
from typing import Any, Generic, TYPE_CHECKING, TypeVar
from uuid import uuid4
import weakref

from psygnal import Signal
from himena import anchor as _anchor
from himena import io
from himena.types import (
    BackendInstructions,
    Parametric,
    WindowState,
    WidgetDataModel,
    WindowRect,
)
from himena._descriptors import (
    ConverterMethod,
    LocalReaderMethod,
    SaveBehavior,
    SaveToNewPath,
    SaveToPath,
    MethodDescriptor,
    ProgramaticMethod,
)

if TYPE_CHECKING:
    from himena.widgets import BackendMainWindow, MainWindow

_W = TypeVar("_W")  # backend widget type
_LOGGER = logging.getLogger(__name__)


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
        widget._himena_widget = self
        if identifier is None:
            identifier = uuid4().int
        self._identifier = identifier

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

    def update_default_save_path(
        self,
        path: str | Path,
        plugin: str | None = None,
    ) -> None:
        """Update the save behavior of the widget."""
        self._save_behavior = SaveToPath(
            path=Path(path), ask_overwrite=True, plugin=plugin
        )
        self._set_modified(False)
        return None

    def _update_widget_data_model_method(self, method: MethodDescriptor | None) -> None:
        """Update the method descriptor of the widget."""
        self._widget_data_model_method = method or ProgramaticMethod()
        return None

    def _set_modified(self, value: bool) -> None:
        """Set the modified state of the widget."""
        if hasattr(self.widget, "set_modified"):
            self.widget.set_modified(value)
        return None


class SubWindow(WidgetWrapper[_W]):
    state_changed = Signal(WindowState)
    renamed = Signal(str)
    closed = Signal()

    def __init__(
        self,
        widget: _W,
        main_window: BackendMainWindow[_W],
        identifier: int | None = None,
    ):
        super().__init__(widget, main_window=main_window, identifier=identifier)
        self._save_behavior: SaveBehavior = SaveToNewPath()
        self._widget_data_model_method: MethodDescriptor = ProgramaticMethod()
        self._child_windows: weakref.WeakSet[SubWindow[_W]] = weakref.WeakSet()
        self._alive = False
        self.closed.connect(self._close_callback)

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}(title={self.title!r}, "
            f"widget={_widget_repr(self.widget)})"
        )

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
    def state(self, value: WindowState | str) -> None:
        main = self._main_window()._himena_main_window
        inst = main._instructions.updated(animate=False)
        self._set_state(value, inst)

    @property
    def rect(self) -> WindowRect:
        """Position and size of the sub-window."""
        return self._main_window()._window_rect(self.widget)

    @rect.setter
    def rect(self, value: tuple[int, int, int, int]) -> None:
        main = self._main_window()._himena_main_window
        inst = main._instructions.updated(animate=False)
        self._set_rect(value, inst)

    @property
    def is_editable(self) -> bool:
        """Whether the widget is editable."""
        is_editable_func = getattr(self.widget, "is_editable", None)
        return callable(is_editable_func) and is_editable_func()

    @is_editable.setter
    def is_editable(self, value: bool) -> None:
        set_editable_func = getattr(self.widget, "set_editable", None)
        if not callable(set_editable_func):
            raise AttributeError("Widget does not have `set_editable` method.")
        set_editable_func(value)

    @property
    def is_importable(self) -> bool:
        """Whether the widget accept importing values."""
        return hasattr(self.widget, "update_model")

    @property
    def is_exportable(self) -> bool:
        """Whether the widget can export its data."""
        return hasattr(self.widget, "to_model")

    @property
    def is_modified(self) -> bool:
        """Whether the content of the widget has been modified."""
        is_modified_func = getattr(self.widget, "is_modified", None)
        return callable(is_modified_func) and is_modified_func()

    @property
    def is_alive(self) -> bool:
        """Whether the sub-window is present in a main window."""
        return self._alive

    def size_hint(self) -> tuple[int, int] | None:
        """Size hint of the sub-window."""
        return getattr(self.widget, "size_hint", _do_nothing)()

    def model_type(self) -> str | None:
        """Type of the widget data model."""
        if not self.is_exportable:
            return None
        _type = getattr(self.widget, "model_type", _do_nothing)()
        if _type is None:
            _type = self.to_model().type
        return _type

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

    def update_model(self, model: WidgetDataModel) -> None:
        """Import the widget data."""
        if not self.is_importable:
            raise ValueError("Widget does not have `update_model` method.")
        self.widget.update_model(model)

    def write_model(self, path: str | Path, plugin: str | None = None) -> None:
        """Write the widget data to a file."""
        return self._write_model(path, plugin, self.to_model())

    def _write_model(
        self, path: str | Path, plugin: str | None, model: WidgetDataModel
    ) -> None:
        path = Path(path)
        io.WriterProviderStore.instance().run(model, path, plugin=plugin)
        self.update_default_save_path(path)
        return None

    def _set_state(self, value: WindowState, inst: BackendInstructions | None = None):
        if inst is None:
            inst = self._main_window()._himena_main_window._instructions
        self._main_window()._set_window_state(self.widget, value, inst)

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
            inst = self._main_window()._himena_main_window._instructions
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

    def add_child(
        self,
        widget: _W,
        *,
        title: str | None = None,
    ) -> SubWindow[_W]:
        """Add a child sub-window, which is automatically closed when the parent is closed."""  # noqa: E501
        main = self._main_window()._himena_main_window
        i_tab, _ = self._find_me(main)
        child = main.tabs[i_tab].add_widget(widget, title=title)
        self._child_windows.add(child)
        return child

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
        for i_tab, tab in main.tabs.enumerate():
            for i_win, win in tab.enumerate():
                # NOTE: should not be `win is self`, because the wrapper may be
                # recreated
                if win.widget is self.widget:
                    return i_tab, i_win
        raise RuntimeError(f"SubWindow {self.title} not found in main window.")

    def _close_me(self, main: MainWindow, confirm: bool = False) -> None:
        if self.is_modified and confirm:
            request = main.exec_choose_one_dialog(
                title="Closing window",
                message=f"Save changes to {self.title!r}?",
                choices=["Yes", "No", "Cancel"],
            )
            if request is None or request == "Cancel":
                return None
            elif request == "Yes" and not self._save_from_dialog(main):
                return None

        i_tab, i_win = self._find_me(main)
        del main.tabs[i_tab][i_win]

    def _save_from_dialog(
        self,
        main: MainWindow,
        behavior: SaveBehavior | None = None,
        plugin: str | None = None,
    ) -> bool:
        """Save this window to a new path, return if saved."""
        if behavior is None:
            behavior = self.save_behavior
        model = self.to_model()
        if save_path := behavior.get_save_path(main, model):
            self._write_model(save_path, plugin=plugin, model=model)
            main.set_status_tip(f"Saved {self.title!r} to {save_path}", duration=5)
            return True
        return False

    def _close_all_children(self, main: MainWindow) -> None:
        for child in self._child_windows:
            child._close_all_children(main)
            if child.is_alive:
                child._close_me(main, confirm=False)

    def _close_callback(self):
        main = self._main_window()._himena_main_window
        self._close_all_children(main)
        self._alive = False

    def _determine_read_from(self) -> tuple[Path, str | None] | None:
        method = self._widget_data_model_method
        if isinstance(method, LocalReaderMethod):
            return method.path, method.plugin
        elif isinstance(save_bh := self.save_behavior, SaveToPath):
            return save_bh.path, None
        else:
            return None

    def _update_from_returned_model(self, model: WidgetDataModel) -> SubWindow[_W]:
        if isinstance(method := model.method, LocalReaderMethod):
            self.update_default_save_path(method.path, plugin=method.plugin)
        elif isinstance(model.method, ConverterMethod):
            self._set_modified(True)
        if (method := model.method) is not None:
            self._update_widget_data_model_method(method)
        return self

    def _is_mergeable_with(self, source: SubWindow[_W]) -> bool:
        widget = self.widget
        if not hasattr(widget, "merge_model"):
            return False
        if hasattr(widget, "mergeable_model_types"):
            types = widget.mergeable_model_types()
            if source.model_type() in types:
                return True
        elif hasattr(widget, "merge_model"):
            return True
        return False

    def _process_merge_model(self, source: SubWindow[_W]) -> bool:
        if hasattr(self.widget, "merge_model"):
            self.widget.merge_model(source.to_model())
            ui = self._main_window()._himena_main_window
            source._close_me(ui)
            ui._backend_main_window._move_focus_to(source.widget)
            return True
        return False


class ParametricWindow(SubWindow[_W]):
    """Subwindow with a parametric widget inside."""

    _IS_PREVIEWING = "is_previewing"
    btn_clicked = Signal(object)  # emit self
    params_changed = Signal(object)  # emit self

    def __init__(
        self,
        widget: _W,
        callback: Parametric,
        main_window: BackendMainWindow[_W],
        identifier: int | None = None,
    ):
        super().__init__(widget, main_window, identifier)
        self._callback = callback
        self.btn_clicked.connect(self._widget_callback)
        self._preview_window_ref = _do_nothing
        self._auto_close = True

        # check if callback has "is_previewing" argument
        sig = callback.get_signature()
        self._has_is_previewing = self._IS_PREVIEWING in sig.parameters

    def get_params(self) -> dict[str, Any]:
        """Get the parameters of the widget."""
        params = self.widget.get_params()
        if not isinstance(params, dict):
            raise TypeError(
                f"`get_param` of {self.widget!r} must return a dict, got {type(params)}"
            )
        return params

    def _get_preview_window(self) -> SubWindow[_W] | None:
        """Return the preview window if it is alive."""
        if (prev := self._preview_window_ref()) and prev.is_alive:
            return prev
        return None

    def _widget_callback(self):
        self._callback_with_params(self.get_params())

    def _widget_preview_callback(self, widget: ParametricWindow):
        if not widget.is_preview_enabled():
            if prev := self._get_preview_window():
                self._preview_window_ref = _do_nothing
                self._child_windows.discard(prev)
                prev._close_me(self._main_window()._himena_main_window)
            return None
        try:
            kwargs = widget.get_params()
            if self._has_is_previewing:
                kwargs[self._IS_PREVIEWING] = True
            return_value = self._callback(**kwargs)
        except Exception as e:
            _LOGGER.warning(f"Error in preview callback: {e}")
            return None
        if not isinstance(return_value, WidgetDataModel):
            raise NotImplementedError("Preview is only supported for WidgetDataModel")
        if prev := self._get_preview_window():
            prev.update_model(return_value)
        else:
            # create a new preview window
            result_widget = widget._model_to_new_window(return_value)
            title = f"{return_value.title} (preview)"
            prev = self.add_child(result_widget, title=title)
            with suppress(AttributeError):
                prev.is_editable = False
            self._preview_window_ref = weakref.ref(prev)
            self._main_window()._move_focus_to(self.widget)
        return None

    def _callback_with_params(self, kwargs: dict[str, Any]):
        if self._has_is_previewing:
            kwargs = {**kwargs, self._IS_PREVIEWING: False}
        return_value = self._callback(**kwargs)
        if isinstance(return_value, WidgetDataModel):
            if prev := self._get_preview_window():
                # no need to create a new window, just use the preview window
                self._preview_window_ref = _do_nothing
                self._child_windows.discard(prev)
                result_widget = prev
                result_widget.title = return_value.title  # title needs update

                # if callback has "is_previewing" argument, the returned value may
                # differ, thus the widget needs update.
                if self._has_is_previewing:
                    result_widget.update_model(return_value)
                with suppress(AttributeError):
                    result_widget.is_editable = True
                if self._auto_close:
                    ui = self._main_window()._himena_main_window
                    self._close_me(ui)
            else:
                result_widget = self._process_model_output(return_value)
            _LOGGER.info("Got subwindow: %r", result_widget)
            if self._callback.sources:
                new_method = self._callback.to_method(kwargs)
                _LOGGER.info(
                    "Inherited method %r, where the original method was %r",
                    new_method,
                    return_value.method,
                )
            else:
                new_method = return_value.method
            result_widget._update_widget_data_model_method(new_method)
            if isinstance(new_method, ConverterMethod):
                result_widget._set_modified(True)
        elif isinstance(return_value, Parametric):
            result_widget = self._process_parametric_output(return_value)
            _LOGGER.info("Got parametric widget: %r", result_widget)
            if self._callback.sources:
                new_method = self._callback.to_method(kwargs)
                result_widget._update_widget_data_model_method(new_method)
                _LOGGER.info("Inherited method: %r", new_method)
        else:
            annot = getattr(self._callback, "__annotations__", {})
            self._process_other_output(return_value, annot.get("return", None))
        return None

    def is_preview_enabled(self) -> bool:
        """Whether the widget supports preview."""
        is_preview_enabled_func = getattr(
            self.widget, "is_preview_enabled", _do_nothing
        )
        return callable(is_preview_enabled_func) and is_preview_enabled_func()

    def _emit_btn_clicked(self) -> None:
        return self.btn_clicked.emit(self)

    def _emit_param_changed(self) -> None:
        return self.params_changed.emit(self)

    def _process_model_output(self, model: WidgetDataModel) -> SubWindow[_W]:
        ui = self._main_window()._himena_main_window
        widget = self._model_to_new_window(model)
        i_tab, i_win = self._find_me(ui)
        if self._auto_close:
            del ui.tabs[i_tab][i_win]
        result_widget = ui.tabs[i_tab].add_widget(
            widget, title=model.title, auto_size=False
        )
        self._coerce_rect(result_widget)
        return result_widget._update_from_returned_model(model)

    def _process_parametric_output(self, fn: Parametric) -> ParametricWindow[_W]:
        ui = self._main_window()._himena_main_window
        i_tab, i_win = self._find_me(ui)
        if self._auto_close:
            del ui.tabs[i_tab][i_win]

        result_widget = ui.add_function(fn, preview=fn.preview)
        self._coerce_rect(result_widget)
        return result_widget

    def _coerce_rect(self, result_widget: SubWindow[_W]):
        rect = self.rect
        if size_hint := result_widget.size_hint():
            new_rect = (rect.left, rect.top, size_hint[0], size_hint[1])
        else:
            new_rect = rect
        result_widget.rect = new_rect
        return None

    def _model_to_new_window(self, model: WidgetDataModel) -> SubWindow[_W]:
        ui = self._main_window()._himena_main_window
        cls = ui._pick_widget_class(model)
        widget = cls()  # the internal widget
        widget.update_model(model)  # type: ignore
        return widget

    def _process_other_output(self, return_value: Any, type_hint: Any | None = None):
        _LOGGER.info("Got output: %r with type hint %r", type(return_value), type_hint)
        ui = self._main_window()._himena_main_window
        ui.model_app.injection_store.process(return_value, type_hint=type_hint)


class DockWidget(WidgetWrapper[_W]):
    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}(title={self.title!r}, "
            f"widget={_widget_repr(self.widget)})"
        )

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


def _widget_repr(widget: _W) -> str:
    return f"<{type(widget).__name__}>"


def _do_nothing() -> None:
    return None
