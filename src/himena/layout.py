from __future__ import annotations

from abc import ABC, abstractmethod
import weakref
import numpy as np
from typing import TYPE_CHECKING, Iterator, MutableSequence
from himena.types import Size, WindowRect, Margins
from himena import anchor as _anc

if TYPE_CHECKING:
    from typing import Self
    from himena.widgets import BackendMainWindow


class Layout(ABC):
    def __init__(self, main: BackendMainWindow | None = None):
        self._anchor = _anc.NoAnchor
        if main:
            self._main_window_ref = weakref.ref(main)
        else:
            self._main_window_ref = lambda: None

    @property
    @abstractmethod
    def rect(self) -> WindowRect:
        """Position and size of the sub-window."""

    @rect.setter
    def rect(self, value: tuple[int, int, int, int] | WindowRect) -> None: ...

    @property
    def size(self) -> Size[int]:
        """Size of the object."""
        return self.rect.size()

    @size.setter
    def size(self, value: tuple[int, int]) -> None:
        self.rect = (self.rect.left, self.rect.top, *value)
        return None

    @property
    def anchor(self) -> _anc.WindowAnchor:
        return self._anchor

    @anchor.setter
    def anchor(self, anchor: _anc.WindowAnchor | None):
        if anchor is None:
            anchor = _anc.NoAnchor
        elif isinstance(anchor, str):
            anchor = self._anchor_from_str(anchor)
        elif not isinstance(anchor, _anc.WindowAnchor):
            raise TypeError(f"Expected WindowAnchor, got {type(anchor)}")
        self._anchor = anchor

    def _reanchor(self, size: Size):
        """Reanchor all windows if needed (such as minimized windows)."""
        if rect := self._anchor.apply_anchor(size, self.size):
            self.rect = rect

    def _anchor_from_str(self, anchor: str):
        rect = self.rect
        main = self._main_window_ref()
        if main is None:
            w0, h0 = 100, 100
        else:
            w0, h0 = self._main_window_ref()._area_size()
        if anchor in ("top-left", "top left", "top_left"):
            return _anc.TopLeftConstAnchor(rect.left, rect.top)
        elif anchor in ("top-right", "top right", "top_right"):
            return _anc.TopRightConstAnchor(w0 - rect.right, rect.top)
        elif anchor in ("bottom-left", "bottom left", "bottom_left"):
            return _anc.BottomLeftConstAnchor(rect.left, h0 - rect.bottom)
        elif anchor in ("bottom-right", "bottom right", "bottom_right"):
            return _anc.BottomRightConstAnchor(w0 - rect.right, h0 - rect.bottom)
        else:
            raise ValueError(f"Unknown anchor: {anchor}")


class LayoutContainer(Layout):
    """Layout that can contain other layouts."""

    def __init__(self, main: BackendMainWindow | None = None):
        self._rect = WindowRect(0, 0, 1000, 1000)
        super().__init__(main)
        self._anchor = _anc.AllCornersAnchor()

    @property
    def rect(self):
        return self._rect

    @rect.setter
    def rect(self, value):
        rect = WindowRect.from_tuple(*value)
        self._rect = rect
        self._resize_children(rect)

    @abstractmethod
    def _resize_children(self, rect: WindowRect):
        """Resize all children layouts based on the geometry of this layout."""


class Layout1D(LayoutContainer, MutableSequence[Layout]):
    """Layout container that arranges children in 1D at the constant interval.

    Properties `margins` and `spacing` are defined as follows.
    ```
            spacing                 margin
             > <                     > <
    [ [child1] [   child2   ] [child3] ]
               <-  stretch ->
    ```

    Abstract methods:
    - `_resize_children(self, rect: WindowRect) -> None`
    - `insert(self, index: int, child: Layout) -> None`
    """

    def __init__(
        self,
        main: BackendMainWindow | None = None,
        *,
        margins: Margins[int] | tuple[int, int, int, int] = (0, 0, 0, 0),
        spacing: int = 0,
    ):
        super().__init__(main)
        self._children: list[Layout] = []
        self._margins = Margins(*margins)
        self._spacing = spacing

    @property
    def margins(self) -> Margins[int]:
        """Margins around the layout."""
        return self._margins

    @margins.setter
    def margins(self, value: Margins[int] | tuple[int, int, int, int]):
        self._margins = Margins(*value)
        self._resize_children(self.rect)

    @property
    def spacing(self) -> int:
        """Spacing between children."""
        return self._spacing

    @spacing.setter
    def spacing(self, value: int):
        if value < 0 or not isinstance(value, (int, np.int_)):
            raise ValueError(f"spacing must be non-negative integer, got {value}")
        self._spacing = value
        self._resize_children(self.rect)

    def set_margins(
        self,
        left: int | None = None,
        top: int | None = None,
        right: int | None = None,
        bottom: int | None = None,
    ):
        margins_old = self.margins
        left = left if left is not None else margins_old.left
        top = top if top is not None else margins_old.top
        right = right if right is not None else margins_old.right
        bottom = bottom if bottom is not None else margins_old.bottom
        self.margins = left, top, right, bottom
        return None

    def __len__(self) -> int:
        return len(self._children)

    def __iter__(self) -> Iterator[Layout]:
        for _, child in self._children:
            yield child

    def __getitem__(self, key) -> Layout:
        _assert_supports_index(key)
        return self._children[key]

    def __setitem__(self, key, layout: Layout):
        if not isinstance(layout, Layout):
            raise TypeError(f"Can only set a Layout object, got {type(layout)}")
        _assert_supports_index(key)
        self._children[key] = layout
        self._resize_children(self.rect)


class BoxLayout1D(Layout1D):
    def __init__(self, main=None, *, margins=(0, 0, 0, 0), spacing=0):
        super().__init__(main, margins=margins, spacing=spacing)
        self._stretches: list[float] = []

    def insert(self, index: int, child: Layout, *, stretch: float = 1) -> None:
        """Insert a child layout at the specified index."""
        if stretch <= 0:
            raise ValueError(f"stretch must be positive, got {stretch!r}")
        self._children.insert(index, child)
        self._stretches.insert(index, float(stretch))
        self._resize_children(self.rect)
        return self

    def append(self, child: Layout, *, stretch: float = 1) -> None:
        return self.insert(len(self), child, stretch=stretch)

    def add(self, child: Layout, *, stretch: float = 1) -> Self:
        self.append(child, stretch=stretch)
        return self

    def __delitem__(self, key):
        _assert_supports_index(key)
        del self._children[key]
        del self._stretches[key]
        self._resize_children(self.rect)

    def add_vbox_layout(self, *, margins=(0, 0, 0, 0), spacing=0) -> VBoxLayout:
        layout = VBoxLayout(self._main_window_ref(), margins=margins, spacing=spacing)
        self.append(layout)
        return layout

    def add_hbox_layout(self, *, margins=(0, 0, 0, 0), spacing=0) -> HBoxLayout:
        layout = HBoxLayout(self._main_window_ref(), margins=margins, spacing=spacing)
        self.append(layout)
        return layout


def _assert_supports_index(key):
    if not hasattr(key, "__index__"):
        raise TypeError(f"{key!r} cannot be used as an index")


class VBoxLayout(BoxLayout1D):
    def _resize_children(self, rect: WindowRect):
        num = len(self._children)
        if num == 0:
            return
        h_cumsum = np.cumsum([0] + self._stretches, dtype=np.float32)
        edges = (h_cumsum / h_cumsum[-1] * rect.height).astype(np.int32)
        width = rect.width - self._margins.left - self._margins.right
        left = rect.left + self._margins.left
        dy = self.spacing // 2
        edges[0] += self._margins.top - dy
        edges[-1] += self._margins.bottom + dy
        for i in range(num):
            top = edges[i] + dy
            height = edges[i + 1] - edges[i] - self.spacing
            irect = WindowRect(left, top, width, height)
            self._children[i].rect = irect
        return None


class HBoxLayout(BoxLayout1D):
    def _resize_children(self, rect: WindowRect):
        num = len(self._children)
        if num == 0:
            return
        w_cumsum = np.cumsum([0] + self._stretches, dtype=np.float32)
        edges = (w_cumsum / w_cumsum[-1] * rect.width).astype(np.int32)
        height = rect.height - self._margins.top - self._margins.bottom
        top = rect.top + self._margins.top
        dx = self.spacing // 2
        edges[0] += self._margins.left - dx
        edges[-1] += self._margins.right + dx
        for i in range(num):
            left = edges[i] + dx
            width = edges[i + 1] - edges[i] - self.spacing
            irect = WindowRect(left, top, width, height)
            self._children[i].rect = irect
        return None


# class GridLayout


class VStackLayout(Layout1D):
    def __init__(
        self,
        main: BackendMainWindow | None = None,
        *,
        margins: Margins[int] | tuple[int, int, int, int] = (0, 0, 0, 0),
        spacing: int = 0,
        inverted: bool = False,
    ):
        super().__init__(main, margins=margins, spacing=spacing)
        self._inverted = inverted

    @property
    def inverted(self) -> bool:
        return self._inverted

    @inverted.setter
    def inverted(self, value: bool):
        self._inverted = bool(value)
        self._resize_children(self.rect)

    def insert(self, index: int, child: Layout) -> None:
        """Insert a child layout at the specified index."""
        self._children.insert(index, child)
        self._resize_children(self.rect)
        return self

    def append(self, child: Layout) -> None:
        return self.insert(len(self), child)

    def add(self, child: Layout) -> Self:
        self.append(child)
        return self

    def __delitem__(self, key):
        _assert_supports_index(key)
        del self._children[key]
        self._resize_children(self.rect)

    def _resize_children(self, rect):
        num = len(self._children)
        if num == 0:
            return
        heights = [ch.rect.height for ch in self._children]
        h_cumsum = np.cumsum([0] + heights, dtype=np.uint32)
        if self._inverted:
            bottoms = rect.bottom - h_cumsum[1:] + self._margins.bottom
            for i, child in enumerate(self._children):
                child.rect = child.rect.move_bottom_left(rect.left, bottoms[i])
        else:
            tops = h_cumsum[:-1] + rect.top + self._margins.top
            for i, child in enumerate(self._children):
                child.rect = child.rect.move_top_left(rect.left, tops[i])
