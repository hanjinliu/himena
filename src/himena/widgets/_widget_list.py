from __future__ import annotations

from abc import abstractmethod
import inspect
from pathlib import Path
from typing import (
    Callable,
    Generic,
    TYPE_CHECKING,
    Hashable,
    Iterator,
    Literal,
    TypeVar,
)
from collections.abc import Sequence
import uuid
import weakref

from psygnal import Signal
from himena import _providers
from himena._descriptors import SaveToPath
from himena.consts import ParametricWidgetProtocolNames as PWPN
from himena.layout import Layout, VBoxLayout, HBoxLayout, VStackLayout
from himena.plugins import _checker
from himena.types import (
    FutureInfo,
    Margins,
    NewWidgetBehavior,
    Size,
    WidgetDataModel,
    WindowState,
    WindowRect,
)
from himena.utils.collections import FrozenList
from himena.workflow import ProgrammaticMethod
from himena.widgets._wrapper import (
    _HasMainWindowRef,
    SubWindow,
    ParametricWindow,
    DockWidget,
)

if TYPE_CHECKING:
    from himena.widgets import BackendMainWindow
    from concurrent.futures import Future

    PathOrPaths = str | Path | list[str | Path]

_W = TypeVar("_W")  # backend widget type
_T = TypeVar("_T")  # type of the default value


class SemiMutableSequence(Sequence[_T]):
    @abstractmethod
    def __delitem__(self, i: int) -> None:
        return NotImplementedError

    def __repr__(self) -> str:
        return f"{type(self).__name__}({list(self)})"

    def clear(self):
        """Clear all the contents of the list."""
        for _ in range(len(self)):
            del self[-1]

    def remove(self, value: _T) -> None:
        """Remove the first occurrence of a value."""
        try:
            i = self.index(value)
        except ValueError:
            raise ValueError("Value not found in the list.")
        del self[i]

    def pop(self, index: int = -1):
        v = self[index]
        del self[index]
        return v

    def len(self) -> int:
        """Length of the list."""
        return len(self)

    def enumerate(self) -> Iterator[tuple[int, _T]]:
        """Method version of enumerate."""
        yield from enumerate(self)

    def iter(self) -> Iterator[_T]:
        """Method version of iter."""
        return iter(self)


class TabArea(SemiMutableSequence[SubWindow[_W]], _HasMainWindowRef[_W]):
    """An area containing multiple sub-windows."""

    def __init__(self, main_window: BackendMainWindow[_W], hash_value: Hashable):
        super().__init__(main_window)
        self._hash_value = hash_value
        # A tab area always has a layout for stacking minimized windows
        self._minimized_window_stack_layout = VStackLayout(main_window, inverted=True)
        self._layouts = [self._minimized_window_stack_layout]
        self._minimized_window_stack_layout._reanchor(Size(*main_window._area_size()))

    @property
    def layouts(self) -> FrozenList[Layout]:
        """List of layouts in the tab area."""
        return FrozenList(self._layouts)

    def _tab_index(self) -> int:
        main = self._main_window()
        for i in range(main._num_tabs()):
            if main._tab_hash(i) == self._hash_value:
                return i
        raise ValueError("Tab is already removed from the main window.")

    def __getitem__(self, index_or_name: int | str) -> SubWindow[_W]:
        index = self._norm_index_or_name(index_or_name)
        widgets = self._main_window()._get_widget_list(self._tab_index())
        front = widgets[index][1]
        return front._himena_widget

    def __delitem__(self, index_or_name: int | str) -> None:
        index = self._norm_index_or_name(index_or_name)
        widget = self._pop_no_emit(index)
        _checker.call_widget_closed_callback(widget.widget)
        widget.closed.emit()

    def _pop_no_emit(self, index: int):
        main = self._main_window()
        win = self[index]
        main._del_widget_at(self._tab_index(), index)
        main._remove_control_widget(win.widget)
        if isinstance(sb := win.save_behavior, SaveToPath):
            main._himena_main_window._history_closed.add((sb.path, sb.plugin))
        return win

    def __len__(self) -> int:
        return len(self._main_window()._get_widget_list(self._tab_index()))

    def __iter__(self) -> Iterator[SubWindow[_W]]:
        return iter(
            w[1]._himena_widget
            for w in self._main_window()._get_widget_list(self._tab_index())
        )

    def append(self, sub_window: SubWindow[_W], title: str) -> None:
        """Append a sub-window to the tab area."""
        main = self._main_window()
        interf, front = sub_window._split_interface_and_frontend()
        front._himena_widget = sub_window
        out = main.add_widget(front, self._tab_index(), title)
        if hasattr(interf, "control_widget"):
            main._set_control_widget(front, interf.control_widget())

        main._connect_window_events(sub_window, out)
        sub_window.title = title
        sub_window.state_changed.connect(main._update_context)

        main._set_current_tab_index(self._tab_index())
        if main._himena_main_window._new_widget_behavior is NewWidgetBehavior.TAB:
            main._set_window_state(
                front,
                WindowState.FULL,
                main._himena_main_window._instructions.updated(animate=False),
            )

        main._move_focus_to(front)
        sub_window._alive = True
        return None

    def current(self, default: _T = None) -> SubWindow[_W] | _T:
        """Get the current sub-window or a default value."""
        idx = self.current_index
        if idx is None:
            return default
        try:
            return self[idx]
        except IndexError:
            return default

    @property
    def name(self) -> str:
        """Name of the tab area."""
        return self._main_window()._get_tab_name_list()[self._tab_index()]

    @property
    def current_index(self) -> int | None:
        """Get the index of the current sub-window."""
        return self._main_window()._current_sub_window_index(self._tab_index())

    @current_index.setter
    def current_index(self, index: int) -> None:
        self._main_window()._set_current_sub_window_index(self._tab_index(), index)

    @property
    def title(self) -> str:
        """Title of the tab area."""
        return self._main_window()._tab_title(self._tab_index())

    def add_widget(
        self,
        widget: _W,
        *,
        title: str | None = None,
        auto_size: bool = True,
    ) -> SubWindow[_W]:
        """Add a widget to the sub window.

        Parameters
        ----------
        widget : QtW.QWidget
            Widget to add.
        title : str, optional
            Title of the sub-window. If not given, its name will be automatically
            generated.

        Returns
        -------
        SubWindow
            A sub-window widget. The added widget is available by calling
            `widget` property.
        """
        main = self._main_window()
        sub_window = SubWindow(widget=widget, main_window=main)
        self._process_new_widget(sub_window, title, auto_size)
        main._move_focus_to(sub_window._split_interface_and_frontend()[1])
        _checker.call_theme_changed_callback(widget, main._himena_main_window.theme)
        return sub_window

    def add_function(
        self,
        func: Callable[..., _T],
        *,
        preview: bool = False,
        title: str | None = None,
        show_parameter_labels: bool = True,
        auto_close: bool = True,
        run_async: bool = False,
        result_as: Literal["window", "below", "right"] = "window",
    ) -> ParametricWindow[_W]:
        """
        Add a function as a parametric sub-window.

        The input function must return a `WidgetDataModel` instance, which can be
        interpreted by the application.

        Parameters
        ----------
        func : function (...) -> WidgetDataModel
            Function that generates a model from the input parameters.
        preview : bool, default False
            If true, the parametric widget will be implemented with a preview toggle
            button, and the preview window will be created when it is enabled.
        title : str, optional
            Title of the parametric window.
        show_parameter_labels : bool, default True
            If true, the parameter labels will be shown in the parametric window.
        auto_close : bool, default True
            If true, close the parametric window after the function call.

        Returns
        -------
        SubWindow
            The sub-window instance that represents the output model.
        """
        sig = inspect.signature(func)
        back_main = self._main_window()
        _is_prev_arg = ParametricWindow._IS_PREVIEWING
        if preview and _is_prev_arg in sig.parameters:
            parameters = [p for p in sig.parameters.values() if p.name != _is_prev_arg]
            sig = sig.replace(parameters=parameters)
        fn_widget = back_main._signature_to_widget(
            sig,
            show_parameter_labels=show_parameter_labels,
            preview=preview,
        )
        param_widget = self.add_parametric_widget(
            fn_widget, func, title=title, preview=preview, run_async=run_async,
            auto_close=auto_close, result_as=result_as,
        )  # fmt: skip
        return param_widget

    def add_parametric_widget(
        self,
        widget: _W,
        callback: Callable | None = None,
        *,
        title: str | None = None,
        preview: bool = False,
        auto_close: bool = True,
        auto_size: bool = True,
        run_async: bool = False,
        result_as: Literal["window", "below", "right"] = "window",
    ) -> ParametricWindow[_W]:
        """Add a custom parametric widget and its callback as a subwindow.

        This method creates a parametric window inside the workspace, so that the
        calculation can be done with the user-defined parameters.

        Parameters
        ----------
        widget : _W
            The parametric widget implemented with `get_params` and/or `get_output`.
        callback : callable, optional
            The callback function that will be called with the parameters set by the
            widget.
        title : str, optional
            Title of the window to manage parameters.
        preview : bool, default False
            If true, the parametric widget will be check for whether preview is enabled
            everytime the parameter changed, and if preview is enabled, a preview window
            is created to show the preview result.
        auto_close : bool, default True
            If true, close the parametric window after the function call.
        auto_size : bool, default True
            If true, the output window will be auto-sized to the size of the parametric
            window.

        Returns
        -------
        ParametricWindow[_W]
            A wrapper containing the backend widget.
        """
        if callback is None:
            if not hasattr(widget, PWPN.GET_OUTPUT):
                raise TypeError(
                    f"Parametric widget must have `{PWPN.GET_OUTPUT}` method if "
                    "callback is not given."
                )
            callback = getattr(widget, PWPN.GET_OUTPUT)
        main = self._main_window()
        widget0 = main._process_parametric_widget(widget)
        param_widget = ParametricWindow(widget0, callback, main_window=main)
        param_widget._auto_close = auto_close
        param_widget._result_as = result_as
        param_widget._run_asynchronously = run_async
        main._connect_parametric_widget_events(param_widget, widget0)
        self._process_new_widget(param_widget, title, auto_size)
        if preview:
            if not (
                hasattr(widget, PWPN.CONNECT_CHANGED_SIGNAL)
                and hasattr(widget, PWPN.IS_PREVIEW_ENABLED)
            ):
                raise TypeError(
                    f"If preview=True, the backend widget {widget!r} must implements "
                    f"methods {PWPN.CONNECT_CHANGED_SIGNAL!r} and "
                    f"{PWPN.IS_PREVIEW_ENABLED!r}"
                )
            param_widget.params_changed.connect(param_widget._widget_preview_callback)
        main._move_focus_to(widget0)
        return param_widget

    def add_vbox_layout(
        self,
        *,
        margins: Margins[int] | tuple[int, int, int, int] = (0, 0, 0, 0),
        spacing: int = 0,
    ) -> VBoxLayout:
        """Add a vertical box layout to the tab area.

        Parameters
        ----------
        margins : (int, int, int, int) or Margins, optional
            Left, top, right and bottom margins of the layout.
        spacing : int, optional
            Spacing between the widgets.
        """
        main = self._main_window()
        layout = VBoxLayout(main, margins=margins, spacing=spacing)
        return self._add_layout(layout)

    def add_hbox_layout(
        self,
        *,
        margins: Margins[int] | tuple[int, int, int, int] = (0, 0, 0, 0),
        spacing: int = 0,
    ) -> HBoxLayout:
        """Add a horizontal box layout to the tab area.

        Parameters
        ----------
        margins : (int, int, int, int) or Margins, optional
            Left, top, right and bottom margins of the layout.
        spacing : int, optional
            Spacing between the widgets.
        """
        main = self._main_window()
        layout = HBoxLayout(main, margins=margins, spacing=spacing)
        return self._add_layout(layout)

    def _add_layout(self, layout: Layout) -> Layout:
        self._layouts.append(layout)
        layout._reanchor(self._main_window()._area_size())
        return layout

    def _process_new_widget(
        self,
        sub_window: SubWindow[_W],
        title: str | None = None,
        auto_size: bool = True,
    ) -> None:
        """Add, resize, and set the focus to the new widget."""
        main = self._main_window()
        interf, front = sub_window._split_interface_and_frontend()
        if title is None:
            title = getattr(interf, "default_title", _make_title)(len(self))
        out = main.add_widget(front, self._tab_index(), title)
        if hasattr(interf, "control_widget"):
            main._set_control_widget(front, interf.control_widget())

        main._connect_window_events(sub_window, out)
        sub_window.title = title
        sub_window.state_changed.connect(main._update_context)

        main._set_current_tab_index(self._tab_index())
        nwindows = len(self)
        if main._himena_main_window._new_widget_behavior is NewWidgetBehavior.TAB:
            main._set_window_state(
                front,
                WindowState.FULL,
                main._himena_main_window._instructions.updated(animate=False),
            )
        else:
            i_tab = main._current_tab_index()
            main._set_current_sub_window_index(i_tab, len(self) - 1)
            if auto_size:
                left = 4 + 24 * (nwindows % 5)
                top = 4 + 24 * (nwindows % 5)
                if size_hint := sub_window.size_hint():
                    width, height = size_hint
                else:
                    _, _, width, height = sub_window.rect
                sub_window.rect = WindowRect(left, top, width, height)
        _checker.call_widget_added_callback(sub_window.widget)
        sub_window._alive = True
        return None

    def add_data_model(self, model: WidgetDataModel) -> SubWindow[_W]:
        """Add a widget data model as a widget."""
        if not isinstance(model, WidgetDataModel):
            raise TypeError(
                f"input model must be an instance of WidgetDataModel, got {model!r}"
            )
        if len(model.workflow) == 0:
            # this case may happen if this method was programatically called
            wf = ProgrammaticMethod(output_model_type=model.type).construct_workflow()
            model = model.model_copy(update={"workflow": wf})
        ui = self._main_window()._himena_main_window
        widget = ui._pick_widget(model)
        ui.set_status_tip(f"Data model {model.title!r} added.", duration=1)
        sub_win = self.add_widget(widget, title=model.title)
        sub_win._update_from_returned_model(model)
        if rect_factory := model.window_rect_override:
            rect = WindowRect.from_tuple(*rect_factory(sub_win.size))
            sub_win.rect = rect
        return sub_win

    def read_file(
        self,
        file_path: PathOrPaths,
        plugin: str | None = None,
    ) -> SubWindow[_W]:
        """Read local file(s) and open as a new sub-window in this tab.

        Parameters
        ----------
        file_path : str or Path or list of them
            Path(s) to the file to read. If a list is given, they will be read as a
            group, not as separate windows.
        plugin : str, optional
            If given, reader provider will be searched with the plugin name. This value
            is usually the full import path to the reader provider function, such as
            `"himena_builtins.io.default_reader_provider"`.

        Returns
        -------
        SubWindow
            The sub-window instance that is constructed based on the return value of
            the reader.
        """
        return self.read_files([file_path], plugin=plugin)[0]

    def read_files(
        self,
        file_paths: PathOrPaths,
        plugin: str | None = None,
    ) -> list[SubWindow[_W]]:
        """Read multiple files and open as new sub-windows in this tab."""
        models = self._paths_to_models(file_paths, plugin=plugin)
        out = [self.add_data_model(model) for model in models]
        ui = self._main_window()._himena_main_window
        if len(out) == 1:
            ui.set_status_tip(f"File opened: {out[0].title}", duration=5)
        elif len(out) > 1:
            _titles = ", ".join(w.title for w in out)
            ui.set_status_tip(f"File opened: {_titles}", duration=5)
        return out

    def _paths_to_models(self, file_paths: PathOrPaths, plugin: str | None = None):
        reader_path_sets: list[tuple[_providers.ReaderTuple, PathOrPaths]] = []
        ins = _providers.ReaderProviderStore.instance()
        file_paths = _norm_paths(file_paths)
        for file_path in file_paths:
            reader_path_sets.append((ins.pick(file_path, plugin=plugin), file_path))
        models = [
            _providers.read_and_update_source(reader, file_path)
            for reader, file_path in reader_path_sets
        ]
        ui = self._main_window()._himena_main_window
        ui._recent_manager.append_recent_files(
            [
                (fp, reader.plugin.to_str() if reader.plugin else None)
                for reader, fp in reader_path_sets
            ]
        )
        return models

    def read_files_async(
        self,
        file_paths: PathOrPaths,
        plugin: str | None = None,
    ) -> Future:
        ui = self._main_window()._himena_main_window
        file_paths = _norm_paths(file_paths)
        future = ui._executor.submit(self._paths_to_models, file_paths, plugin=plugin)
        if len(file_paths) == 1:
            ui.set_status_tip(f"Opening: {file_paths[0].as_posix()}", duration=5)
        else:
            ui.set_status_tip(f"Opening {len(file_paths)} files", duration=5)
        FutureInfo(list[WidgetDataModel]).set(future)  # set info for injection store
        return future

    def save_session(
        self,
        file_path: str | Path,
        save_copies: bool = False,
        allow_calculate: Sequence[str] = (),
    ) -> None:
        """Save the current session to a file."""
        from himena.session import dump_tab_to_zip

        dump_tab_to_zip(
            self, file_path, save_copies=save_copies, allow_calculate=allow_calculate
        )
        return None

    def tile_windows(
        self,
        nrows: int | None = None,
        ncols: int | None = None,
    ) -> None:
        main = self._main_window()
        inst = main._himena_main_window._instructions
        width, height = main._area_size()
        nrows, ncols = _norm_nrows_ncols(nrows, ncols, len(self))

        w = width / ncols
        h = height / nrows
        for i in range(nrows):
            for j in range(ncols):
                idx = i * ncols + j
                if idx >= len(self):
                    break
                x = j * width / ncols
                y = i * height / nrows
                sub = self[idx]
                rect = WindowRect.from_tuple(x, y, w, h)
                main._set_window_rect(sub.widget, rect, inst)
        return None

    def _norm_index_or_name(self, index_or_name: int | str) -> int:
        if isinstance(index_or_name, str):
            for i, w in enumerate(
                self._main_window()._get_widget_list(self._tab_index())
            ):
                if w[0] == index_or_name:
                    index = i
                    break
            else:
                raise ValueError(f"Name {index_or_name!r} not found.")
        else:
            if index_or_name < 0:
                index = len(self) + index_or_name
            else:
                index = index_or_name
        return index


def _norm_nrows_ncols(nrows: int | None, ncols: int | None, n: int) -> tuple[int, int]:
    if nrows is None:
        if ncols is None:
            nrows = int(n**0.5)
            ncols = int(n / nrows)
        else:
            nrows = int(n / ncols)
    elif ncols is None:
        ncols = int(n / nrows)
    return nrows, ncols


class TabList(SemiMutableSequence[TabArea[_W]], _HasMainWindowRef[_W], Generic[_W]):
    changed = Signal()

    def __init__(self, main_window: BackendMainWindow[_W]):
        super().__init__(main_window)
        self._tab_areas: dict[Hashable, TabArea] = {}

    def __getitem__(self, index_or_name: int | str) -> TabArea[_W]:
        index = self._norm_index_or_name(index_or_name)
        main = self._main_window()
        out = self._tab_areas.get(main._tab_hash(index))
        if out is None:
            raise ValueError(f"Tab index {index} not found in the list.")
        return out

    def __delitem__(self, index_or_name: int | str) -> None:
        index = self._norm_index_or_name(index_or_name)
        area = self[index]
        area.clear()
        main = self._main_window()
        hash = main._tab_hash(index)
        self._tab_areas.pop(hash)
        main._del_tab_at(index)
        self.changed.emit()
        return None

    def add(self, name: str) -> TabArea[_W]:
        main = self._main_window()
        n_tab = len(self)
        if name is None:
            name = f"Tab-{n_tab}"
        main.add_tab(name)
        self.changed.emit()
        main._set_current_tab_index(n_tab)
        area = TabArea(main, main._tab_hash(n_tab))
        self._tab_areas[area._hash_value] = area
        main._himena_main_window._tab_activated(n_tab)
        return area

    def get(self, index_or_name: int | str, /) -> TabArea[_W] | None:
        try:
            return self[index_or_name]
        except ValueError:
            return None

    def __len__(self) -> int:
        return len(self._main_window()._get_tab_name_list())

    def __iter__(self):
        main = self._main_window()
        for i in range(main._num_tabs()):
            hash = main._tab_hash(i)
            yield self._tab_areas[hash]

    def _norm_index_or_name(self, index_or_name: int | str) -> int:
        if isinstance(index_or_name, str):
            index = self.names.index(index_or_name)
        else:
            if index_or_name < 0:
                index = len(self) + index_or_name
            else:
                index = index_or_name
        return index

    @property
    def names(self) -> list[str]:
        """List of names of the tabs."""
        return self._main_window()._get_tab_name_list()

    def current(self, default: _T = None) -> TabArea[_W] | _T:
        """Get the current tab or a default value."""
        idx = self.current_index
        if idx is None:
            return default
        try:
            return self[idx]
        except (IndexError, ValueError):
            return default

    @property
    def current_index(self) -> int | None:
        """Get the index of the current tab (None of nothing exists)."""
        return self._main_window()._current_tab_index()

    @current_index.setter
    def current_index(self, index: int):
        self._main_window()._set_current_tab_index(index)


class DockWidgetList(
    SemiMutableSequence[DockWidget[_W]], _HasMainWindowRef[_W], Generic[_W]
):
    def __init__(self, main_window: BackendMainWindow[_W]):
        super().__init__(main_window)
        self._dock_widget_set = weakref.WeakValueDictionary[DockWidget[_W], _W]()

    def __getitem__(self, index: int) -> DockWidget[_W]:
        return list(self._dock_widget_set.keys())[index]

    def __delitem__(self, index: int) -> None:
        dock = self[index]
        self._main_window()._del_dock_widget(dock.widget)
        self._dock_widget_set.pop(dock)

    def __len__(self) -> int:
        return len(self._dock_widget_set)

    def __iter__(self) -> Iterator[DockWidget[_W]]:
        return iter(self._dock_widget_set.keys())

    def __repr__(self) -> str:
        return f"{type(self).__name__}({list(self)})"

    def _add_dock_widget(self, dock: DockWidget[_W]) -> None:
        self._dock_widget_set[dock] = dock.widget
        return None

    def widget_for_id(self, id: uuid.UUID) -> DockWidget[_W] | None:
        """Pick the dock widget by its ID."""
        for _dock in self:
            if id != _dock._identifier:
                continue
            return _dock
        return None


def _make_title(i: int) -> str:
    return f"Untitled-{i}"


def _norm_paths(file_paths: PathOrPaths) -> list[Path | list[Path]]:
    if isinstance(file_paths, (str, Path)):
        file_paths = [file_paths]
    out = []
    for file_path in file_paths:
        if isinstance(file_path, (str, Path)):
            file_path = Path(file_path)
        else:
            file_path = [Path(p) for p in file_path]
        out.append(file_path)
    return out
