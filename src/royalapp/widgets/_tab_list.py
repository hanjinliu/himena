from __future__ import annotations

from abc import abstractmethod
from typing import Generic, TYPE_CHECKING, Iterator, TypeVar
from collections.abc import Sequence

from psygnal import Signal
from royalapp.types import NewWidgetBehavior, SubWindowState, WindowRect
from royalapp.widgets._wrapper import _HasMainWindowRef, SubWindow

if TYPE_CHECKING:
    from royalapp.widgets import BackendMainWindow

_W = TypeVar("_W")  # backend widget type
_T = TypeVar("_T")  # type of the default value


class SemiMutableSequence(Sequence[_T]):
    @abstractmethod
    def __delitem__(self, i: int) -> None:
        return NotImplementedError

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
        return len(self)

    def enumerate(self):
        yield from enumerate(self)

    def iter(self):
        return iter(self)


class TabArea(SemiMutableSequence[SubWindow[_W]], _HasMainWindowRef[_W]):
    """An area containing multiple sub-windows."""

    def __init__(self, main_window: BackendMainWindow[_W], i_tab: int):
        super().__init__(main_window)
        self._i_tab = i_tab

    def __repr__(self) -> str:
        return f"{type(self).__name__}({list(self)})"

    def __getitem__(self, index_or_name: int | str) -> SubWindow[_W]:
        index = self._norm_index_or_name(index_or_name)
        backend_widget = self._main_window()._get_widget_list(self._i_tab)[index][1]
        return backend_widget._royalapp_widget

    def __setitem__(self, i: int, value: _W) -> None:
        return NotImplementedError

    def __delitem__(self, index_or_name: int | str) -> None:
        index = self._norm_index_or_name(index_or_name)
        return self._main_window()._del_widget_at(self._i_tab, index)

    def _norm_index_or_name(self, index_or_name: int | str) -> int:
        if isinstance(index_or_name, str):
            index = self.window_titles.index(index_or_name)
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
            w[1]._royalapp_widget
            for w in self._main_window()._get_widget_list(self._i_tab)
        )

    def append(self, sub_window: SubWindow[_W], title: str) -> None:
        main = self._main_window()
        out = main.add_widget(sub_window.widget, self._i_tab, title)

        main._connect_window_events(sub_window, out)
        sub_window.title = title
        sub_window.state_changed.connect(main._update_context)

        main._set_current_tab_index(self._i_tab)
        with main._royalapp_main_window._animation_context(enabled=False):
            if main._royalapp_main_window._new_widget_behavior is NewWidgetBehavior.TAB:
                nwindows = len(self)
                main._set_window_state(
                    self._i_tab,
                    nwindows - 1,
                    SubWindowState.FULL,
                )

        main._move_focus_to(sub_window.widget)
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

    @property
    def window_titles(self) -> list[str]:
        """List of names of the sub-windows."""
        return [w[0] for w in self._main_window()._get_widget_list(self._i_tab)]

    def add_widget(
        self,
        widget: _W,
        *,
        title: str | None = None,
        autosize: bool = True,
    ) -> SubWindow[_W]:
        """
        Add a widget to the sub window.

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
        if title is None:
            title = "Window"
        out = main.add_widget(sub_window.widget, self._i_tab, title)

        main._connect_window_events(sub_window, out)
        sub_window.title = title
        sub_window.state_changed.connect(main._update_context)

        main._set_current_tab_index(self._i_tab)
        with main._royalapp_main_window._animation_context(enabled=False):
            if main._royalapp_main_window._new_widget_behavior is NewWidgetBehavior.TAB:
                nwindows = len(self)
                main._set_window_state(
                    self._i_tab,
                    nwindows - 1,
                    SubWindowState.FULL,
                )
            else:
                main._set_current_sub_window_index(len(self) - 1)
                if autosize and (size_hint := sub_window.size_hint()):
                    left, top, _, _ = sub_window.window_rect
                    sub_window.window_rect = WindowRect(left, top, *size_hint)
        main._move_focus_to(widget)
        return sub_window

    def tile_windows(
        self,
        nrows: int | None = None,
        ncols: int | None = None,
    ) -> None:
        main = self._main_window()
        inst = main._royalapp_main_window._instructions
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

    def __repr__(self) -> str:
        return f"{type(self).__name__}({list(self)})"

    def __getitem__(self, index_or_name: int | str) -> TabArea[_W]:
        index = self._norm_index_or_name(index_or_name)
        return TabArea(self._main_window(), index)

    def __setitem__(self, i: int, value: TabArea[_W]) -> None:
        return NotImplementedError

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

    def append(self, value: TabArea[_W]) -> None:
        self._main_window().add_tab(value)
        self.changed.emit()
        return None

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
