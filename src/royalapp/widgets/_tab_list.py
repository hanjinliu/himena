from __future__ import annotations

from abc import abstractmethod
from typing import Generic, TYPE_CHECKING, Iterable, Iterator, TypeVar
from collections.abc import Sequence

from psygnal import Signal
from royalapp.types import WindowRect
from royalapp.widgets._wrapper import _HasMainWindowRef, SubWindow

if TYPE_CHECKING:
    from royalapp.widgets import BackendMainWindow

_W = TypeVar("_W")  # backend widget type
_T = TypeVar("_T")  # type of the default value


class SemiMutableSequence(Sequence[_W]):
    @abstractmethod
    def __delitem__(self, i: int) -> None:
        return NotImplementedError

    def clear(self):
        """Clear all the contents of the list."""
        for _ in range(len(self)):
            del self[-1]

    def remove(self, value: _W) -> None:
        """Remove the first occurrence of a value."""
        try:
            i = self.index(value)
        except ValueError:
            raise ValueError("Value not found in the list.")
        del self[i]

    @abstractmethod
    def append(self, value: _W) -> None: ...

    def extend(self, values: Iterable[_W]) -> None:
        if values is self:
            values = list(values)
        for v in values:
            self.append(v)

    def pop(self, index: int = -1) -> _W:
        v = self[index]
        del self[index]
        return v

    def len(self) -> int:
        return len(self)

    def enumerate(self) -> Iterator[tuple[int, _W]]:
        yield from enumerate(self)

    def iter(self) -> Iterator[_W]:
        return iter(self)


class TabArea(SemiMutableSequence[_W], _HasMainWindowRef[_W]):
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

    def append(self, value: _W, /) -> None:
        return self._main_window().add_widget(value)

    def current(self, default: _T = None) -> SubWindow[_W] | _T:
        """Get the current sub-window or a default value."""
        idx = self.current_index()
        if idx is None:
            return default
        try:
            return self[idx]
        except IndexError:
            return default

    def current_index(self) -> int | None:
        return self._main_window()._current_sub_window_index()

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
        sub_window = SubWindow(widget=widget, main_window=self._main_window())
        title = self._coerce_window_title(title)
        out = self._main_window().add_widget(sub_window.widget, self._i_tab, title)
        self._main_window()._connect_window_events(sub_window, out)
        sub_window.title = title
        return sub_window

    def tile_windows(
        self,
        nrows: int | None = None,
        ncols: int | None = None,
    ) -> None:
        main = self._main_window()
        width, height = main._area_size()
        if nrows is None:
            if ncols is None:
                nrows = int(len(self) ** 0.5)
                ncols = int(len(self) / nrows)
            else:
                nrows = int(len(self) / ncols)
        elif ncols is None:
            ncols = int(len(self) / nrows)

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
                main._set_window_rect(sub.widget, WindowRect.from_numbers(x, y, w, h))

    def _coerce_window_title(self, title: str | None) -> str:
        existing = set(self.window_titles)
        if title is None:
            title = "Window"
        title_original = title
        count = 0
        while title in existing:
            title = f"{title_original}-{count}"
            count += 1
        return title


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
        idx = self.current_index()
        if idx is None:
            return default
        try:
            return self[idx]
        except IndexError:
            return default

    def current_index(self) -> int | None:
        return self._main_window()._current_tab_index()
