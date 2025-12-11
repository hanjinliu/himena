from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Iterator, NamedTuple
from psygnal import Signal


if TYPE_CHECKING:
    Range = tuple[slice[int, int, None], slice[int, int, None]]


class Index(NamedTuple):
    """Index tuple,"""

    row: int
    column: int

    def as_uint(self) -> Index:
        """Return unsigned Index"""
        return Index(max(self.row, 0), max(self.column, 0))


class DummyRange(NamedTuple):
    row: slice
    column: slice


_DUMMY_RANGE = DummyRange(slice(0, 0), slice(0, 0))


class SelectionModel:
    """A specialized range model with item-selection-like behavior."""

    moving = Signal(Index, Index)
    moved = Signal(Index, Index)

    def __init__(self, row_count: Callable[[], int], col_count: Callable[[], int]):
        self._ranges: list[Range] = []
        self._is_blocked = False
        self._selected_indices: set[int] = set()

        # indices of self._ranges that are row/column selections
        self._row_selection_indices: set[int] = set()
        self._col_selection_indices: set[int] = set()

        self._ctrl_on = False
        self._shift_on = False
        self._selection_start: Index | None = None
        self._current_index = Index(0, 0)
        self._row_count_getter = row_count
        self._col_count_getter = col_count

    @property
    def current_index(self) -> Index:
        """Current position of the selection cursor."""
        return self._current_index

    @current_index.setter
    def current_index(self, index: tuple[int, int]):
        self._current_index = Index(*index)

    @property
    def current_range(self) -> Range | None:
        if len(self._ranges) > 0:
            return self._ranges[-1]

    @property
    def start(self) -> Index | None:
        """The selection starting index."""
        return self._selection_start

    def __len__(self) -> int:
        """Number of ranges"""
        return len(self._ranges)

    def __iter__(self) -> Iterator[Range]:
        """Iterate over all the ranges."""
        return iter(self._ranges)

    def __getitem__(self, index: int) -> Range:
        """Get the range at the specified index."""
        return self._ranges[index]

    @property
    def ranges(self) -> list[Range]:
        return list(self._ranges)

    def get_single_range(self) -> Range:
        """Return the only range in the selection model."""
        if len(self._ranges) == 0:
            r, c = self.current_index
            return (slice(r, r + 1), slice(c, c + 1))
        elif len(self._ranges) == 1:
            return self._ranges[0]
        raise ValueError("Multiple ranges are selected.")

    def iter_row_selections(self) -> Iterator[slice]:
        for i in self._row_selection_indices:
            yield self._ranges[i][0]

    def iter_col_selections(self) -> Iterator[slice]:
        for i in self._col_selection_indices:
            yield self._ranges[i][1]

    def num_row_selections(self) -> int:
        return len(self._row_selection_indices)

    def num_col_selections(self) -> int:
        return len(self._col_selection_indices)

    def append(self, range: Range, row: bool = False, column: bool = False) -> None:
        """Append a new range."""
        if self._is_blocked:
            return None
        self._ranges.append(range)
        if row:
            self._row_selection_indices.add(len(self._ranges) - 1)
        elif column:
            self._col_selection_indices.add(len(self._ranges) - 1)

    def update_last(self, range: Range, row: bool = False, col: bool = False) -> None:
        """Update the last range with new one."""
        if self._is_blocked:
            return None
        if self._ranges:
            self._ranges[-1] = range
        else:
            self._ranges.append(range)
        if row:
            self._row_selection_indices.add(len(self._ranges) - 1)
        elif col:
            self._col_selection_indices.add(len(self._ranges) - 1)

    def contains(self, index: tuple[int, int]) -> bool:
        """Whether the index is in the selection."""
        r0, c0 = index
        for r, c in self._ranges:
            if r.start <= r0 < r.stop and c.start <= c0 < c.stop:
                return True
        return False

    def set_ranges(self, ranges: list[Range]) -> None:
        if self._is_blocked:
            return None
        self.clear()
        return self._ranges.extend(ranges)

    def clear(self) -> None:
        """Clear all the selections"""
        if self._is_blocked:
            return None
        self._ranges.clear()
        self._row_selection_indices.clear()
        self._col_selection_indices.clear()

    def is_jumping(self) -> bool:
        """Whether the selection is jumping or not."""
        return len(self._ranges) > 0 and self._ranges[-1] is _DUMMY_RANGE

    def is_moving_to_edge(self) -> bool:
        """Whether the selection is moving to the edge by Ctrl+arrow key."""
        return not self.is_jumping() and self._ctrl_on

    def set_ctrl(self, on: bool) -> None:
        """Equivalent to pressing Ctrl."""
        self._ctrl_on = bool(on)

    def set_shift(self, on: bool) -> None:
        """Equivalent to pressing Shift."""
        self._shift_on = bool(on)
        if on and self._selection_start is None:
            self._selection_start = self._current_index

    def jump_to(self, r: int, c: int):
        """Emulate mouse click at cell (r, c)."""
        if self._ctrl_on and not self._shift_on:
            self._ranges.append(_DUMMY_RANGE)
        return self.move_to(r, c)

    def move_to(self, r: int, c: int):
        """Emulate dragging to cell (r, c)."""
        src = self._current_index
        dst = Index(r, c)
        self.moving.emit(src, dst)
        self._current_index = dst
        if self._is_blocked:
            return None

        if not self._shift_on:
            self._selection_start = None

        if self._selection_start is None:
            _r0 = _r1 = r
            _c0 = _c1 = c
        else:
            r0, c0 = self._selection_start
            _r0, _r1 = sorted([r0, r])
            _c0, _c1 = sorted([c0, c])

        if _r0 < 0:
            rsl = slice(0, self._row_count_getter())
            col = True
        else:
            rsl = slice(_r0, _r1 + 1)
            col = False
        if _c0 < 0:
            csl = slice(0, self._col_count_getter())
            row = True
        else:
            csl = slice(_c0, _c1 + 1)
            row = False

        if not self._shift_on:
            if not self.is_jumping():
                self.clear()
        elif self._selection_start is None:
            self._selection_start = self._current_index

        self.update_last((rsl, csl), row=row, col=col)
        self.moved.emit(src, dst)

    def move(self, dr: int, dc: int, allow_header: bool = False):
        """Move by (dr, dc) cells."""
        r, c = self._current_index
        idx_min = -int(allow_header)

        if dr != 0:
            nr = self._row_count_getter()
            r = min(r + dr, nr - 1)
            r = max(idx_min, r)

        if dc != 0:
            nc = self._col_count_getter()
            c = min(c + dc, nc - 1)
            c = max(idx_min, c)

        return self.move_to(r, c)

    def move_limited(self, dr: int, dc: int, nr: int, nc: int):
        """Move by (dr, dc) cells within the range of (nr, nc)."""
        r, c = self._current_index
        r_new = _move_limited_one(r, dr, nr)
        c_new = _move_limited_one(c, dc, nc)
        return self.move_to(r_new, c_new)


def _move_limited_one(r: int, dr: int, nr: int):
    if r < nr:
        r = min(max(0, r + dr), nr - 1)
    else:  # already out of range
        r = max(0, r + dr)
    return r
