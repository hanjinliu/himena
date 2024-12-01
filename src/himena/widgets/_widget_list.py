from __future__ import annotations

from abc import abstractmethod
from logging import getLogger
import inspect
from pathlib import Path
from typing import Callable, Generic, TYPE_CHECKING, Iterator, TypeVar
from collections.abc import Sequence
import weakref

from psygnal import Signal
from himena import _providers
from himena._descriptors import SaveToPath
from himena.consts import ParametricWidgetProtocolNames as PWPN
from himena.plugins import _checker
from himena.types import (
    NewWidgetBehavior,
    WidgetDataModel,
    WindowState,
    WindowRect,
)
from himena.widgets._wrapper import (
    _HasMainWindowRef,
    SubWindow,
    ParametricWindow,
    DockWidget,
)

if TYPE_CHECKING:
    from himena.widgets import BackendMainWindow

    PathOrPaths = str | Path | list[str | Path]

_W = TypeVar("_W")  # backend widget type
_T = TypeVar("_T")  # type of the default value
_LOGGER = getLogger(__name__)


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

    def __init__(self, main_window: BackendMainWindow[_W], i_tab: int):
        super().__init__(main_window)
        self._i_tab = i_tab

    def __getitem__(self, index_or_name: int | str) -> SubWindow[_W]:
        index = self._norm_index_or_name(index_or_name)
        widgets = self._main_window()._get_widget_list(self._i_tab)
        backend_widget = widgets[index][1]
        return backend_widget._himena_widget

    def __delitem__(self, index_or_name: int | str) -> None:
        index = self._norm_index_or_name(index_or_name)
        widget = self._pop_no_emit(index)
        _checker.call_window_closed_callback(widget.widget)
        widget.closed.emit()

    def _pop_no_emit(self, index: int):
        main = self._main_window()
        win = self[index]
        main._del_widget_at(self._i_tab, index)
        main._remove_control_widget(win.widget)
        if isinstance(sb := win.save_behavior, SaveToPath):
            main._himena_main_window._history_closed.add((sb.path, sb.plugin))
        return win

    def _norm_index_or_name(self, index_or_name: int | str) -> int:
        if isinstance(index_or_name, str):
            index = self.collect_titles().index(index_or_name)
        else:
            if index_or_name < 0:
                index = len(self) + index_or_name
            else:
                index = index_or_name
        return index

    def __len__(self) -> int:
        return len(self._main_window()._get_widget_list(self._i_tab))

    def __iter__(self) -> Iterator[SubWindow[_W]]:
        return iter(
            w[1]._himena_widget
            for w in self._main_window()._get_widget_list(self._i_tab)
        )

    def append(self, sub_window: SubWindow[_W], title: str) -> None:
        main = self._main_window()
        inner_widget = sub_window.widget
        out = main.add_widget(inner_widget, self._i_tab, title)
        if hasattr(inner_widget, "control_widget"):
            main._set_control_widget(inner_widget, inner_widget.control_widget())

        main._connect_window_events(sub_window, out)
        sub_window.title = title
        sub_window.state_changed.connect(main._update_context)

        main._set_current_tab_index(self._i_tab)
        if main._himena_main_window._new_widget_behavior is NewWidgetBehavior.TAB:
            main._set_window_state(
                inner_widget,
                WindowState.FULL,
                main._himena_main_window._instructions.updated(animate=False),
            )

        main._move_focus_to(inner_widget)
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
        return self._main_window()._get_tab_name_list()[self._i_tab]

    @property
    def current_index(self) -> int | None:
        """Get the index of the current sub-window."""
        return self._main_window()._current_sub_window_index()

    @current_index.setter
    def current_index(self, index: int) -> None:
        self._main_window()._set_current_sub_window_index(index)

    @property
    def title(self) -> str:
        """Title of the tab area."""
        return self._main_window()._tab_title(self._i_tab)

    def collect_titles(self) -> list[str]:
        """List of names of the sub-windows."""
        return [w[0] for w in self._main_window()._get_widget_list(self._i_tab)]

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
        main._move_focus_to(widget)
        return sub_window

    def add_function(
        self,
        func: Callable[..., _T],
        *,
        preview: bool = False,
        title: str | None = None,
        show_parameter_labels: bool = True,
        auto_close: bool = True,
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
            fn_widget,
            func,
            title=title,
            preview=preview,
            auto_close=auto_close,
        )
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

    def _process_new_widget(
        self,
        sub_window: SubWindow[_W],
        title: str | None = None,
        auto_size: bool = True,
    ) -> None:
        main = self._main_window()
        if title is None:
            title = "Window"
        inner_widget = sub_window.widget
        out = main.add_widget(inner_widget, self._i_tab, title)
        if hasattr(inner_widget, "control_widget"):
            main._set_control_widget(inner_widget, inner_widget.control_widget())

        main._connect_window_events(sub_window, out)
        sub_window.title = title
        sub_window.state_changed.connect(main._update_context)

        main._set_current_tab_index(self._i_tab)
        nwindows = len(self)
        if main._himena_main_window._new_widget_behavior is NewWidgetBehavior.TAB:
            main._set_window_state(
                inner_widget,
                WindowState.FULL,
                main._himena_main_window._instructions.updated(animate=False),
            )
        else:
            main._set_current_sub_window_index(len(self) - 1)
            if auto_size:
                left = 4 + 24 * (nwindows % 5)
                top = 4 + 24 * (nwindows % 5)
                if size_hint := sub_window.size_hint():
                    width, height = size_hint
                else:
                    _, _, width, height = sub_window.rect
                sub_window.rect = WindowRect(left, top, width, height)
        sub_window._alive = True
        return None

    def add_data_model(self, model: WidgetDataModel) -> SubWindow[_W]:
        """Add a widget data model as a widget."""
        ui = self._main_window()._himena_main_window
        cls = ui._pick_widget_class(model)
        _LOGGER.debug("Picked widget class: %s", cls)
        # construct the internal widget
        try:
            widget = cls(ui)
        except TypeError:
            widget = cls()
        widget.update_model(model)  # type: ignore
        sub_win = self.add_widget(widget, title=model.title)
        return sub_win._update_from_returned_model(model)

    def read_file(
        self,
        file_path: PathOrPaths,
        plugin: str | None = None,
    ) -> SubWindow[_W]:
        """Read local file(s) and open as a new sub-window in this tab."""
        return self.read_files([file_path], plugin=plugin)[0]

    def read_files(
        self,
        file_paths: PathOrPaths,
        plugin: str | None = None,
    ) -> list[SubWindow[_W]]:
        """Read multiple files and open as new sub-windows in this tab."""
        reader_path_sets: list[tuple[_providers.ReaderTuple, PathOrPaths]] = []
        ins = _providers.ReaderProviderStore.instance()
        for file_path in file_paths:
            if isinstance(file_path, (str, Path)):
                file_path = Path(file_path)
            else:
                file_path = [Path(p) for p in file_path]
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
        out = [self.add_data_model(model) for model in models]
        if len(out) == 1:
            ui.set_status_tip(f"File opened: {out[0].title}", duration=5)
        elif len(out) > 1:
            _titles = ", ".join(w.title for w in out)
            ui.set_status_tip(f"File opened: {_titles}", duration=5)
        return out

    def save_session(self, file_path: str | Path) -> None:
        """Save the current session to a file."""
        from himena.session import TabSession

        file_path = self._main_window()._himena_main_window.exec_file_dialog(
            mode="w",
            extension_default=".session.yaml",
            allowed_extensions=[".session.yaml"],
        )
        if file_path is None:
            return None
        session = TabSession.from_gui(self)
        session.dump_yaml(file_path)
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
                rect = WindowRect.from_numbers(x, y, w, h)
                main._set_window_rect(sub.widget, rect, inst)
        return None


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

    def __getitem__(self, index_or_name: int | str) -> TabArea[_W]:
        index = self._norm_index_or_name(index_or_name)
        return TabArea(self._main_window(), index)

    def __delitem__(self, index_or_name: int | str) -> None:
        index = self._norm_index_or_name(index_or_name)
        area = self[index]
        area.clear()
        self._main_window()._del_tab_at(index)
        self.changed.emit()
        return None

    def __len__(self) -> int:
        return len(self._main_window()._get_tab_name_list())

    def __iter__(self):
        main = self._main_window()
        return iter(TabArea(main, i) for i in range(len(self)))

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
        except IndexError:
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

    def widget_for_id(self, id: str) -> DockWidget[_W] | None:
        for _dock in self:
            if id != _dock._identifier:
                continue
            return _dock
        return None
