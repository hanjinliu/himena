from __future__ import annotations

from abc import ABC, abstractmethod
from contextlib import contextmanager
from functools import cache
import weakref
import numpy as np
from typing import TYPE_CHECKING, Any, Callable, Iterable, Iterator, MutableSequence
from himena.types import Size, WindowRect, Margins
from himena import anchor as _anc
from himena._utils import iter_subclasses


if TYPE_CHECKING:
    from typing import Self
    from himena.widgets import BackendMainWindow, MainWindow


class Layout(ABC):
    def __init__(self, main: BackendMainWindow | None = None):
        self._anchor = _anc.NoAnchor
        if main:
            self._main_window_ref = weakref.ref(main)
        else:
            self._main_window_ref = _no_ref
        self._parent_layout_ref: Callable[[], LayoutContainer | None] = _no_ref

    @property
    @abstractmethod
    def rect(self) -> WindowRect:
        """Position and size of the sub-window."""

    @rect.setter
    def rect(self, value: tuple[int, int, int, int] | WindowRect) -> None: ...

    @abstractmethod
    def _serialize_layout(self) -> Any:
        """Serialize the layout instance."""

    @classmethod
    @abstractmethod
    def _deserialize_layout(cls, obj, main: MainWindow) -> Any:
        """Deserialize the layout instance."""

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
            w0, h0 = main._area_size()
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


@cache
def get_layout_class(typ: str) -> type[Layout]:
    for ly in iter_subclasses(Layout):
        if ly.__name__.lower() == typ:
            return ly
    raise ValueError(f"Unknown layout type: {typ}")


def construct_layout(obj, main: MainWindow) -> Layout:
    cls = get_layout_class(obj["type"])
    return cls._deserialize_layout(obj, main)


def _no_ref() -> None:
    return None


class EmptyLayout(Layout):
    """A layout that does not contain anything."""

    def __init__(self, main: BackendMainWindow | None = None):
        super().__init__(main)
        self._rect = WindowRect(0, 0, 0, 0)

    @property
    def rect(self):
        return self._rect

    @rect.setter
    def rect(self, value):
        rect_old = self._rect
        self._rect = WindowRect.from_tuple(*value)
        if parent := self._parent_layout_ref():
            parent._adjust_child_resize(self, rect_old, self._rect)

    def _serialize_layout(self):
        return {"type": "empty", "rect": self.rect}

    @classmethod
    def _deserialize_layout(cls, obj, main: MainWindow):
        self = cls(main._backend_main_window)
        self.rect = obj["rect"]
        return self


class LayoutContainer(Layout):
    """Layout that can contain other layouts."""

    def __init__(self, main: BackendMainWindow | None = None):
        self._rect = WindowRect(0, 0, 1000, 1000)
        super().__init__(main)
        self._anchor = _anc.AllCornersAnchor()
        self._is_calling_adjust_child_resize = False

    @contextmanager
    def _adjust_child_resize_context(self):
        was = self._is_calling_adjust_child_resize
        self._is_calling_adjust_child_resize = True
        try:
            yield
        finally:
            self._is_calling_adjust_child_resize = was

    @property
    def rect(self):
        return self._rect

    @rect.setter
    def rect(self, value):
        rect = WindowRect.from_tuple(*value)
        rect_old = self._rect
        self._rect = rect
        self._resize_children(rect)
        if parent := self._parent_layout_ref():
            parent._adjust_child_resize(self, rect_old, rect)

    @abstractmethod
    def _resize_children(self, rect: WindowRect):
        """Resize all children layouts based on the geometry of this layout."""

    @abstractmethod
    def remove(self, child: Layout) -> None:
        """Remove a child layout from this layout."""

    # @abstractmethod
    def _adjust_child_resize(
        self, child: Layout, rect_old: WindowRect, rect_new: WindowRect
    ):
        """Adjust layout container based on the child resize/move."""


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
        *,
        left: int | None = None,
        top: int | None = None,
        right: int | None = None,
        bottom: int | None = None,
    ):
        """Update margins around the layout."""
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

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self._children!r})"

    def __getitem__(self, key) -> Layout:
        _assert_supports_index(key)
        return self._children[key]

    def __setitem__(self, key, layout: Layout):
        if not isinstance(layout, Layout):
            raise TypeError(f"Can only set a Layout object, got {type(layout)}")
        _assert_supports_index(key)
        self._children[key] = layout
        layout._parent_layout_ref = weakref.ref(self)
        self._resize_children(self.rect)

    def remove(self, child: Layout) -> None:
        MutableSequence.remove(self, child)
        child._parent_layout_ref = _no_ref
        if len(self) > 1:
            self._resize_children(self.rect)
        elif len(self) == 1:
            self.remove(self[0])

    def _serialize_layout(self):
        return {
            "type": type(self).__name__.lower(),
            "children": [child._serialize_layout() for child in self._children],
            "margins": list(self.margins),
            "spacing": self.spacing,
        }

    @classmethod
    def _deserialize_layout(cls, obj, main: MainWindow) -> Self:
        self = cls(
            main._backend_main_window, margins=obj["margins"], spacing=obj["spacing"]
        )
        for child_obj in obj["children"]:
            child = construct_layout(child_obj, main)
            self.append(child)
        return self


class BoxLayout1D(Layout1D):
    def __init__(self, main=None, *, margins=(0, 0, 0, 0), spacing=0):
        super().__init__(main, margins=margins, spacing=spacing)
        self._stretches: list[float] = []

    def insert(self, index: int, child: Layout, *, stretch: float = 1) -> None:
        """Insert a child layout at the specified index."""
        if stretch <= 0:
            raise ValueError(f"stretch must be positive, got {stretch!r}")
        if not isinstance(child, Layout):
            raise TypeError(f"Can only insert a Layout object, got {type(child)}")
        self._children.insert(index, child)
        child._parent_layout_ref = weakref.ref(self)
        self._stretches.insert(index, float(stretch))
        self._resize_children(self.rect)
        return self

    def append(self, child: Layout, *, stretch: float = 1) -> None:
        return self.insert(len(self), child, stretch=stretch)

    def add(
        self,
        child: Layout | Iterable[Layout],
        *more: Layout,
        stretch: float = 1,
    ) -> Self:
        """Add child layout(s) to the layout."""
        if not isinstance(child, Layout):
            child, more = child[0], [*child[1:], *more]
        self.append(child, stretch=stretch)
        for ch in more:
            self.append(ch, stretch=stretch)
        return self

    def __delitem__(self, key: int):
        _assert_supports_index(key)
        child = self._children.pop(key)
        child._parent_layout_ref = _no_ref
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

    def _may_take_child(
        self, child: Layout, rect_old: WindowRect, rect_new: WindowRect
    ) -> Layout:
        # window moved
        dist2 = (rect_old.top - rect_new.top) ** 2 + (
            rect_old.left - rect_new.left
        ) ** 2
        if dist2 > 60**2:
            # remove window from the layout
            self.remove(child)
        self._resize_children(self.rect)


def _assert_supports_index(key):
    if not hasattr(key, "__index__"):
        raise TypeError(f"{key!r} cannot be used as an index")


class VBoxLayout(BoxLayout1D):
    """A vertical box layout."""

    def _iter_edge_and_span(self, rect: WindowRect) -> Iterator[tuple[int, int]]:
        num = len(self._children)
        if num == 0:
            yield from ()
            return
        h_cumsum = np.cumsum([0] + self._stretches, dtype=np.float32)
        edges = (h_cumsum / h_cumsum[-1] * rect.height).astype(np.int32)
        dy = self.spacing // 2
        edges[0] += self._margins.top - dy
        edges[-1] += self._margins.bottom + dy
        for i in range(num):
            top = edges[i] + dy
            height = edges[i + 1] - edges[i] - self.spacing
            yield top, height

    def _ortho_region(self, rect: WindowRect) -> tuple[int, int]:
        width = rect.width - self._margins.left - self._margins.right
        left = rect.left + self._margins.left
        return left, width

    def _resize_children(self, rect: WindowRect):
        left, width = self._ortho_region(rect)
        with self._adjust_child_resize_context():
            for i, (top, height) in enumerate(self._iter_edge_and_span(rect)):
                irect = WindowRect(left, top, width, height)
                self._children[i].rect = irect
        return None

    def _adjust_child_resize(self, child: Layout, rect_old, rect_new):
        if self._is_calling_adjust_child_resize:
            return
        top_changed = rect_old.top != rect_new.top
        bottom_changed = rect_old.bottom != rect_new.bottom
        with self._adjust_child_resize_context():
            if top_changed and bottom_changed:
                return self._may_take_child(child, rect_old, rect_new)

            top, height = self._ortho_region(self.rect)
            new_rect = child.rect
            stretches = self._stretches.copy()
            for i, (left, width) in enumerate(self._iter_edge_and_span(self.rect)):
                stretches[i] = width
                if top_changed and self._children[i] is child:
                    if i == 0:
                        child.rect = WindowRect(left, top, width, height)
                    else:
                        old_sum = stretches[i - 1] + stretches[i]
                        stretches[i - 1] = old_sum - new_rect.height
                        stretches[i] = new_rect.height
                elif bottom_changed and self._children[i - 1] is child:
                    if i == len(self) - 1:
                        child.rect = WindowRect(left, top, width, height)
                    else:
                        old_sum = stretches[i - 1] + stretches[i]
                        stretches[i] = old_sum - new_rect.height
                        stretches[i - 1] = new_rect.height
                else:
                    child.rect = WindowRect(left, top, width, height)
            self._stretches = stretches
            self._resize_children(self.rect)


class HBoxLayout(BoxLayout1D):
    """A horizontal box layout."""

    def _iter_edge_and_span(self, rect: WindowRect) -> Iterator[tuple[int, int]]:
        num = len(self._children)
        if num == 0:
            yield from ()
            return
        w_cumsum = np.cumsum([0] + self._stretches, dtype=np.float32)
        edges = (w_cumsum / w_cumsum[-1] * rect.width).astype(np.int32)
        dx = self.spacing // 2
        edges[0] += self._margins.left - dx
        edges[-1] += self._margins.right + dx
        for i in range(num):
            left = edges[i] + dx
            width = edges[i + 1] - edges[i] - self.spacing
            yield left, width

    def _ortho_region(self, rect: WindowRect) -> tuple[int, int]:
        height = rect.height - self._margins.top - self._margins.bottom
        top = rect.top + self._margins.top
        return top, height

    def _resize_children(self, rect: WindowRect):
        top, height = self._ortho_region(rect)
        with self._adjust_child_resize_context():
            for i, (left, width) in enumerate(self._iter_edge_and_span(rect)):
                irect = WindowRect(left, top, width, height)
                self._children[i].rect = irect
        return None

    def _adjust_child_resize(self, child: Layout, rect_old, rect_new):
        if self._is_calling_adjust_child_resize:
            return
        left_changed = rect_old.left != rect_new.left
        right_changed = rect_old.right != rect_new.right
        with self._adjust_child_resize_context():
            if left_changed and right_changed:
                return self._may_take_child(child, rect_old, rect_new)

            top, height = self._ortho_region(self.rect)
            new_rect = child.rect
            stretches = self._stretches.copy()
            for i, (left, width) in enumerate(self._iter_edge_and_span(self.rect)):
                stretches[i] = width
                if left_changed and self._children[i] is child:
                    if i == 0:
                        child.rect = WindowRect(left, top, width, height)
                    else:
                        old_sum = stretches[i - 1] + stretches[i]
                        w0 = stretches[i - 1] = old_sum - new_rect.width
                        self._children[i - 1].rect = self._children[
                            i - 1
                        ].rect.with_width(w0)
                        stretches[i] = new_rect.width
                elif right_changed and self._children[i - 1] is child:
                    if i == len(self) - 1:
                        child.rect = WindowRect(left, top, width, height)
                    else:
                        old_sum = stretches[i - 1] + stretches[i]
                        w0 = stretches[i] = old_sum - new_rect.width
                        self._children[i].rect = new_rect.with_width(w0)
                        stretches[i - 1] = new_rect.width
                else:
                    child.rect = WindowRect(left, top, width, height)
            self._stretches = stretches
            self._resize_children(self.rect)


class GridLayout(LayoutContainer):
    def __init__(
        self,
        main: BackendMainWindow | None = None,
        *,
        margins: Margins[int] | tuple[int, int, int, int] = (0, 0, 0, 0),
        spacing: Size[int] | tuple[int, int] = 0,
    ):
        super().__init__(main)
        self._margins = Margins(*margins)
        self._spacing = Size(*spacing)

    @property
    def margins(self) -> Margins[int]:
        """Margins around the layout."""
        return self._margins

    @margins.setter
    def margins(self, value: Margins[int] | tuple[int, int, int, int]):
        self._margins = Margins(*value)
        self._resize_children(self.rect)

    @property
    def spacing(self) -> Size:
        """Spacing between children."""
        return self._spacing

    @spacing.setter
    def spacing(self, value: Size[int] | tuple[int, int]):
        self._spacing = Size(*value)
        self._resize_children(self.rect)


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
        child._parent_layout_ref = weakref.ref(self)
        self._resize_children(self.rect)
        return self

    def append(self, child: Layout) -> None:
        return self.insert(len(self), child)

    def add(self, child: Layout) -> Self:
        self.append(child)
        return self

    def __delitem__(self, key: int):
        _assert_supports_index(key)
        self._children[key]._parent_layout_ref = _no_ref
        del self._children[key]
        self._resize_children(self.rect)

    def _resize_children(self, rect):
        num = len(self._children)
        if num == 0:
            return
        heights = [ch.rect.height for ch in self._children]
        h_cumsum = np.cumsum([0] + heights, dtype=np.uint32)
        if self._inverted:
            bottoms = rect.bottom - h_cumsum[:-1] + self._margins.bottom
            for i, child in enumerate(self._children):
                child.rect = child.rect.move_bottom_left(rect.left, bottoms[i])
        else:
            tops = h_cumsum[:-1] + rect.top + self._margins.top
            for i, child in enumerate(self._children):
                child.rect = child.rect.move_top_left(rect.left, tops[i])
