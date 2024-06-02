from __future__ import annotations

from abc import abstractmethod
from typing import Generic, TYPE_CHECKING, Iterable, Iterator, TypeVar
from collections.abc import Sequence
import weakref

from psygnal import Signal
from royalapp.types import SubWindowState, WidgetDataModel

if TYPE_CHECKING:
    from royalapp.widgets import BackendMainWindow

_W = TypeVar("_W")  # backend widget type
_T = TypeVar("_T")  # type of the default value


class _HasMainWindowRef(Generic[_W]):
    def __init__(self, main_window: BackendMainWindow[_W]):
        self._main_window_ref = weakref.ref(main_window)

    def _main_window(self) -> BackendMainWindow[_W]:
        out = self._main_window_ref()
        if out is None:
            raise RuntimeError("Main window was deleted")
        return out


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

    def __getitem__(self, index_or_name: int | str) -> _W:
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
            index = self.titles.index(index_or_name)
        else:
            if index_or_name < 0:
                index = len(self) + index_or_name
            else:
                index = index_or_name
        return index

    def __len__(self) -> int:
        return len(self._main_window()._get_widget_list(self._i_tab))

    def __iter__(self):
        return iter(w[1] for w in self._main_window()._get_widget_list(self._i_tab))

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
    def titles(self) -> list[str]:
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

    def _coerce_window_title(self, title: str | None) -> str:
        existing = set(self.titles)
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


class SubWindow(_HasMainWindowRef[_W], Generic[_W]):
    state_changed = Signal(SubWindowState)
    closed = Signal()

    def __init__(self, widget: _W, main_window: BackendMainWindow[_W]):
        super().__init__(main_window)
        self._widget = weakref.ref(widget)
        widget._royalapp_widget = self

    def __repr__(self) -> str:
        return f"{type(self).__name__}(title={self.title!r}, widget={self.widget!r})"

    def __class_getitem__(cls, widget_type: type[_W]):
        return cls

    @property
    def widget(self) -> _W:
        """Get the internal backend widget."""
        if out := self._widget():
            return out
        raise RuntimeError("Widget was deleted.")

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
