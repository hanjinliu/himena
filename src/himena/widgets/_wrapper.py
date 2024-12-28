"""Widget wrappers."""

from __future__ import annotations

from concurrent.futures import Future
from contextlib import suppress
import inspect
import logging
from pathlib import Path
from typing import Any, Callable, Generic, TYPE_CHECKING, Literal, TypeVar
from uuid import uuid4
import weakref

from psygnal import Signal
from magicgui import widgets as mgw
from himena import anchor as _anchor
from himena import _providers
from himena._utils import get_gui_config, get_widget_class_id
from himena.consts import ParametricWidgetProtocolNames as PWPN
from himena.types import (
    BackendInstructions,
    DragDataModel,
    DropResult,
    ModelTrack,
    Parametric,
    ParametricWidgetProtocol,
    Size,
    WindowState,
    WidgetDataModel,
    WindowRect,
)
from himena._descriptors import (
    ConverterMethod,
    LocalReaderMethod,
    NoNeedToSave,
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
        if identifier is None:
            identifier = uuid4().int
        self._identifier = identifier
        self._save_behavior: SaveBehavior = SaveToNewPath()
        self._widget_data_model_method: MethodDescriptor = ProgramaticMethod()
        self._is_modified_fallback_value = False
        self._frontend_widget()._himena_widget = self

    @property
    def is_alive(self) -> bool:
        """Whether the widget is present in a main window."""
        # by default, always return True
        return True

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
        if isinstance(self._save_behavior, SaveToPath):
            ask_overwrite = self._save_behavior.ask_overwrite
        else:
            ask_overwrite = True
        self._save_behavior = SaveToPath(
            path=Path(path), ask_overwrite=ask_overwrite, plugin=plugin
        )
        self._set_modified(False)
        return None

    def _update_widget_data_model_method(
        self,
        method: MethodDescriptor | None,
        overwrite: bool = True,
    ) -> None:
        """Update the method descriptor of the widget."""
        if isinstance(self._widget_data_model_method, ProgramaticMethod) or overwrite:
            self._widget_data_model_method = method or ProgramaticMethod()
            _LOGGER.info("Method of %r updated to %r", self, method)
        return None

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
        if hasattr(self.widget, "is_modified"):
            return self.widget.is_modified()
        return self._is_modified_fallback_value

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

    def _set_modified(self, value: bool) -> None:
        """Set the modified state of the widget."""
        if hasattr(self.widget, "set_modified"):
            self.widget.set_modified(value)
        else:
            if value and not self.is_exportable:
                # If the backend widget cannot be converted to a model, there's no need
                # to inform the user "save changes?".
                return None
            self._is_modified_fallback_value = value
        return None

    def size_hint(self) -> tuple[int, int] | None:
        """Size hint of the sub-window."""
        return getattr(self.widget, "size_hint", _do_nothing)()

    def model_type(self) -> str | None:
        """Type of the widget data model."""
        if not self.is_exportable:
            return None
        interf = self.widget
        _type = None
        if hasattr(interf, "model_type"):
            _type = interf.model_type()
        elif hasattr(interf, "__himena_model_type__"):
            _type = interf.__himena_model_type__
        if _type is None:
            _type = self.to_model().type
        return _type

    def update_model(self, model: WidgetDataModel) -> None:
        """Import the widget data."""
        if not self.is_importable:
            raise ValueError("Widget does not have `update_model` method.")
        self.widget.update_model(model)

    def _is_mergeable_with(self, incoming: DragDataModel) -> bool:
        widget = self.widget
        if hasattr(widget, "allowed_drop_types"):
            types = widget.allowed_drop_types()
            if incoming.type is None:
                return True  # not specified. Just allow it.
            if incoming.type in types:
                return True
        elif hasattr(widget, "dropped_callback"):
            return True
        return False

    def _process_drop_event(
        self,
        incoming: DragDataModel,
        source: SubWindow[_W] | None = None,
    ) -> bool:
        if hasattr(self.widget, "dropped_callback"):
            # to remember how the model was mapped to a widget class
            model = incoming.data_model()
            if source is not None:
                model.force_open_with = get_widget_class_id(source.widget)
            merge_result = self.widget.dropped_callback(model)
            if merge_result is None:
                merge_result = DropResult()
            ui = self._main_window()._himena_main_window
            if outputs := merge_result.outputs:
                ui.model_app.injection_store.process(outputs)
            if source is not None:
                if merge_result.delete_input:
                    source._close_me(ui)
                ui._backend_main_window._move_focus_to(source._frontend_widget())
            return True
        return False

    def _split_interface_and_frontend(self) -> tuple[object, _W]:
        """Split the interface that defines methods and the frontend widget.

        This function is used to separate the interface object that implements the
        himena protocols and the actual widget that will be added to the main window.
        """
        obj = self.widget
        if hasattr(obj, "native_widget"):
            front = obj.native_widget()
        elif isinstance(obj, mgw.Widget):
            front = obj.native
        else:
            front = obj
        return obj, front

    def _frontend_widget(self) -> _W:
        """Get the frontend widget."""
        return self._split_interface_and_frontend()[1]


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
        return self._main_window()._window_title(self._frontend_widget())

    @title.setter
    def title(self, value: str) -> None:
        self._main_window()._set_window_title(self._frontend_widget(), value)

    @property
    def state(self) -> WindowState:
        """State (e.g. maximized, minimized) of the sub-window."""
        return self._main_window()._window_state(self._frontend_widget())

    @state.setter
    def state(self, value: WindowState | str) -> None:
        main = self._main_window()._himena_main_window
        inst = main._instructions.updated(animate=False)
        self._set_state(value, inst)

    @property
    def rect(self) -> WindowRect:
        """Position and size of the sub-window."""
        return self._main_window()._window_rect(self._frontend_widget())

    @rect.setter
    def rect(self, value: tuple[int, int, int, int]) -> None:
        main = self._main_window()._himena_main_window
        inst = main._instructions.updated(animate=False)
        self._set_rect(value, inst)

    @property
    def size(self) -> Size[int]:
        """Size of the sub-window."""
        return self.rect.size()

    @size.setter
    def size(self, value: tuple[int, int]) -> None:
        self.rect = (self.rect.left, self.rect.top, value[0], value[1])

    @property
    def is_alive(self) -> bool:
        """Whether the sub-window is present in a main window."""
        return self._alive

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

        if model.title is None:
            model.title = self.title
        if model.method is None:
            model.method = self._widget_data_model_method
        return model

    def write_model(self, path: str | Path, plugin: str | None = None) -> None:
        """Write the widget data to a file."""
        return self._write_model(path, plugin, self.to_model())

    def _write_model(
        self, path: str | Path, plugin: str | None, model: WidgetDataModel
    ) -> None:
        path = Path(path)
        ins = _providers.WriterProviderStore.instance()
        if path.suffix == ".pickle":
            ins.run(model, path, plugin=plugin)
        else:
            ins.run(model, path, plugin=plugin, min_priority=0)
        self.update_default_save_path(path)
        return None

    def _set_state(self, value: WindowState, inst: BackendInstructions | None = None):
        if inst is None:
            inst = self._main_window()._himena_main_window._instructions
        self._main_window()._set_window_state(self._frontend_widget(), value, inst)

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
        front = self._frontend_widget()
        rect = WindowRect.from_tuple(*value)
        anc = main._window_anchor(front).update_for_window_rect(main._area_size(), rect)
        main._set_window_rect(front, rect, inst)
        main._set_window_anchor(front, anc)

    @property
    def anchor(self) -> _anchor.WindowAnchor:
        """Anchor of the sub-window."""
        return self._main_window()._window_anchor(self._frontend_widget())

    @anchor.setter
    def anchor(self, anchor: _anchor.WindowAnchor | None):
        if anchor is None:
            anchor = _anchor.NoAnchor
        elif isinstance(anchor, str):
            anchor = self._anchor_from_str(anchor)
        elif not isinstance(anchor, _anchor.WindowAnchor):
            raise TypeError(f"Expected WindowAnchor, got {type(anchor)}")
        self._main_window()._set_window_anchor(self._frontend_widget(), anchor)

    def update(
        self,
        *,
        rect: tuple[int, int, int, int] | None = None,
        state: WindowState | None = None,
        title: str | None = None,
        anchor: _anchor.WindowAnchor | str | None = None,
    ) -> SubWindow[_W]:
        """A helper method to update window properties."""
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
            if isinstance(self.save_behavior, SaveToNewPath):
                message = f"{self.title!r} is not saved yet. Save before closing?"
            else:
                message = f"Save changes to {self.title!r}?"
            request = main.exec_choose_one_dialog(
                title="Closing window",
                message=message,
                choices=["Save", "Don't save", "Cancel"],
            )
            if request is None or request == "Cancel":
                return None
            elif request == "Save" and not self._save_from_dialog(main):
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
        """Close all the sub-windows that are children of this window."""
        for child in self._child_windows:
            child._close_all_children(main)
            if child.is_alive:
                child._close_me(main, confirm=False)

    def _close_callback(self):
        main = self._main_window()._himena_main_window
        self._close_all_children(main)
        self._alive = False

    def _determine_read_from(self) -> tuple[Path | list[Path], str | None] | None:
        method = self._widget_data_model_method
        if isinstance(method, LocalReaderMethod):
            return method.path, method.plugin
        elif isinstance(save_bh := self.save_behavior, SaveToPath):
            return save_bh.path, None
        else:
            return None

    def _update_from_returned_model(self, model: WidgetDataModel) -> SubWindow[_W]:
        """Update the sub-window based on the returned model."""
        if isinstance(method := model.method, LocalReaderMethod):
            # file is directly read from the local path
            if isinstance(save_path := method.path, Path):
                self.update_default_save_path(save_path, plugin=method.plugin)
        elif isinstance(model.method, ConverterMethod):
            # model is created by some converter function
            if not isinstance(model.save_behavior_override, NoNeedToSave):
                self._set_modified(True)
        if (method := model.method) is not None:
            self._update_widget_data_model_method(method)
        if save_behavior_override := model.save_behavior_override:
            self._save_behavior = save_behavior_override
        if not model.editable:
            with suppress(AttributeError):
                self.is_editable = False
        return self

    def _switch_to_file_watch_mode(self):
        # TODO: don't use Qt in the future
        from himena.qt._qtwatchfiles import QWatchFileObject

        self.title = f"[Preview] {self.title}"
        QWatchFileObject(self)
        return None


class ParametricWindow(SubWindow[_W]):
    """Subwindow with a parametric widget inside."""

    _IS_PREVIEWING = "is_previewing"  # keyword argument used for preview flag
    btn_clicked = Signal(object)  # emit self
    params_changed = Signal(object)  # emit self

    def __init__(
        self,
        widget: _W,
        callback: Callable,
        main_window: BackendMainWindow[_W],
        identifier: int | None = None,
    ):
        super().__init__(widget, main_window, identifier)
        self._callback = callback
        self.btn_clicked.connect(self._widget_callback)
        self._preview_window_ref: Callable[[], WidgetWrapper[_W] | None] = _do_nothing
        self._auto_close = True
        self._run_asynchronously = False
        self._last_future: Future | None = None
        self._result_as: Literal["window", "below", "right"] = "window"

        # check if callback has "is_previewing" argument
        sig = inspect.signature(callback)
        self._has_is_previewing = self._IS_PREVIEWING in sig.parameters
        self._return_annotation = sig.return_annotation

    def get_params(self) -> dict[str, Any]:
        """Get the parameters of the widget."""
        if hasattr(self.widget, PWPN.GET_PARAMS):
            params = getattr(self.widget, PWPN.GET_PARAMS)()
            if not isinstance(params, dict):
                raise TypeError(
                    f"`{PWPN.GET_PARAMS}` of {self.widget!r} must return a dict, got "
                    f"{type(params)}."
                )
        else:
            params = {}
        return params

    def _get_preview_window(self) -> SubWindow[_W] | None:
        """Return the preview window if it is alive."""
        if (prev := self._preview_window_ref()) and prev.is_alive:
            return prev
        return None

    def _widget_callback(self):
        """Callback when the call button is clicked."""
        main = self._main_window()
        main._set_parametric_widget_busy(self, True)
        try:
            self._callback_with_params(self.get_params())
        finally:
            main._set_parametric_widget_busy(self, False)

    def _call(self, **kwargs):
        """Call the callback asynchronously."""
        ui = self._main_window()._himena_main_window
        if self._run_asynchronously:
            if self._last_future is not None:
                self._last_future.cancel()
                self._last_future = None
            self._last_future = future = ui._executor.submit(self._callback, **kwargs)
            return future
        else:
            return self._callback(**kwargs)

    def _widget_preview_callback(self):
        main = self._main_window()
        if not self.is_preview_enabled():
            if prev := self._get_preview_window():
                self._preview_window_ref = _do_nothing
                self._child_windows.discard(prev)
                if self._result_as == "window":
                    prev._close_me(main._himena_main_window)
                else:
                    main._remove_widget_from_parametric_window(self)
                    if hint := self.size_hint():
                        self.rect = (self.rect.left, self.rect.top, hint[0], hint[1])
            return None
        kwargs = self.get_params()
        if self._has_is_previewing:
            kwargs[self._IS_PREVIEWING] = True
        # TODO: check async
        return_value = self._callback(**kwargs)
        if return_value is None:
            return None
        if not isinstance(return_value, WidgetDataModel):
            raise NotImplementedError(
                "Preview is only supported for WidgetDataModel but the return value "
                f"was {type(return_value)}"
            )
        if prev := self._get_preview_window():
            prev.update_model(return_value)
        else:
            # create a new preview window
            result_widget = self._model_to_new_window(return_value)
            if self._result_as == "window":
                title = f"{return_value.title} (preview)"
                prev = self.add_child(result_widget, title=title)
                with suppress(AttributeError):
                    prev.is_editable = False
            else:
                main._add_widget_to_parametric_window(
                    self, result_widget, self._result_as
                )
                # update the size because new window is added
                if hint := self.size_hint():
                    self.rect = (self.rect.left, self.rect.top, hint[0], hint[1])
                prev = WidgetWrapper(result_widget, main)  # just for wrapping
            self._preview_window_ref = weakref.ref(prev)
            main._move_focus_to(self._frontend_widget())
        return None

    def _process_return_value(self, return_value: Any, kwargs: dict[str, Any]):
        tracker = self._get_model_track()
        _LOGGER.info("Got tracker: %r", tracker)
        ui = self._main_window()._himena_main_window
        if isinstance(return_value, WidgetDataModel):
            if prev := self._get_preview_window():
                # no need to create a new window, just use the preview window
                self._preview_window_ref = _do_nothing
                if self._result_as != "window":
                    widget = prev.widget  # avoid garbage collection
                    self._main_window()._remove_widget_from_parametric_window(self)
                    result_widget = ui.add_widget(widget)
                    result_widget._update_from_returned_model(return_value)
                else:
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
                    self._close_me(ui)
            else:
                result_widget = self._process_model_output(return_value)
            _LOGGER.info("Got subwindow: %r", result_widget)
            if tracker.command_id is not None:
                new_method = tracker.to_method(kwargs)
                _LOGGER.info(
                    "Inherited method %r, where the original method was %r",
                    new_method,
                    return_value.method,
                )
            else:
                new_method = return_value.method
            result_widget._update_widget_data_model_method(new_method, overwrite=False)
            if isinstance(new_method, ConverterMethod):
                if not isinstance(return_value.save_behavior_override, NoNeedToSave):
                    result_widget._set_modified(True)
        elif self._return_annotation in (Parametric, ParametricWidgetProtocol):
            is_func = self._return_annotation == Parametric
            result_widget = self._process_parametric_output(
                return_value, is_func=is_func
            )
            _LOGGER.info("Got parametric widget: %r", result_widget)
            if tracker.command_id is not None:
                new_method = tracker.to_method(kwargs)
                result_widget._update_widget_data_model_method(
                    new_method, overwrite=False
                )
                _LOGGER.info("Inherited method: %r", new_method)
        else:
            annot = getattr(self._callback, "__annotations__", {})
            if isinstance(return_value, Future):
                injection_type_hint = Future
                # This is hacky. The injection store will process the result but the
                # return type cannot be inherited from the callback. Here, we just set
                # the type hint to Future and let it processed in the
                # "_future_done_callback" method of himena application.
                return_value._ino_type_hint = annot.get("return", None)
                return_value._himena_descriptor = tracker.to_method(kwargs)
            else:
                injection_type_hint = annot.get("return", None)
            self._process_other_output(return_value, injection_type_hint)
        return None

    def _callback_with_params(self, kwargs: dict[str, Any]):
        if self._has_is_previewing:
            kwargs = {**kwargs, self._IS_PREVIEWING: False}
        main = self._main_window()
        try:
            return_value = self._call(**kwargs)
        except Exception:
            main._set_parametric_widget_busy(self, False)
            raise
        if isinstance(return_value, Future):
            main._add_job_progress(return_value, desc=self.title, total=0)
            return_value.add_done_callback(
                main._process_future_done_callback(
                    self._process_return_value,
                    kwargs=kwargs,
                )
            )
            return_value.add_done_callback(
                lambda _: main._set_parametric_widget_busy(self, False)
            )
            return None
        else:
            main._set_parametric_widget_busy(self, False)
            return self._process_return_value(return_value, kwargs)

    def _get_model_track(self) -> ModelTrack:
        default = ModelTrack()
        model_track = getattr(
            self._callback,
            "__himena_model_track__",
            getattr(self.widget, "__himena_model_track__", None),
        )
        if not isinstance(model_track, ModelTrack):
            model_track = default
        return model_track

    def is_preview_enabled(self) -> bool:
        """Whether the widget supports preview."""
        isfunc = getattr(self.widget, PWPN.IS_PREVIEW_ENABLED, None)
        return callable(isfunc) and isfunc()

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

    def _process_parametric_output(
        self,
        out,
        is_func: bool = True,
    ) -> ParametricWindow[_W]:
        ui = self._main_window()._himena_main_window
        if self._auto_close:
            self._close_me(ui)
        if is_func:
            result_widget = ui.add_function(out, **get_gui_config(out))
        else:
            result_widget = ui.add_parametric_widget(out, **get_gui_config(out))
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

    def _model_to_new_window(self, model: WidgetDataModel) -> _W:
        ui = self._main_window()._himena_main_window
        widget = ui._pick_widget(model)
        return widget

    def _process_other_output(self, return_value: Any, type_hint: Any | None = None):
        _LOGGER.info("Got output: %r with type hint %r", type(return_value), type_hint)
        ui = self._main_window()._himena_main_window
        ui.model_app.injection_store.process(return_value, type_hint=type_hint)
        if self._auto_close:
            self._close_me(ui)


class DockWidget(WidgetWrapper[_W]):
    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}(title={self.title!r}, "
            f"widget={_widget_repr(self.widget)})"
        )

    @property
    def visible(self) -> bool:
        """Visibility of the dock widget."""
        return self._main_window()._dock_widget_visible(self._frontend_widget())

    @visible.setter
    def visible(self, visible: bool) -> bool:
        return self._main_window()._set_dock_widget_visible(
            self._frontend_widget(), visible
        )

    def show(self) -> None:
        """Show the dock widget."""
        self.visible = True

    def hide(self) -> None:
        """Hide the dock widget."""
        self.visible = False

    @property
    def title(self) -> str:
        """Title of the dock widget."""
        return self._main_window()._dock_widget_title(self._frontend_widget())

    @title.setter
    def title(self, title: str) -> None:
        return self._main_window()._set_dock_widget_title(
            self._frontend_widget(), str(title)
        )


def _widget_repr(widget: _W) -> str:
    wid = get_widget_class_id(type(widget))
    return f"<{wid}>"


def _do_nothing() -> None:
    return None
