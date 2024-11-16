from __future__ import annotations

from typing import TypeVar, Generic

_T = TypeVar("_T")


class HistoryContainer(Generic[_T]):
    def __init__(self, max_size: int = 20):
        self._hist: list[_T] = []
        self._max_size = max_size

    def add(self, item: _T) -> None:
        self._hist.append(item)
        if len(self._hist) > self._max_size:
            self._hist.pop(0)

    def get(self, num: int) -> _T | None:
        """Get the item at the given index if exists."""
        if len(self._hist) > num:
            return self._hist[num]
        return None

    def get_from_last(self, num: int) -> _T | None:
        """Get the item at the given index from the last if exists."""
        if len(self._hist) >= num:
            return self._hist[-num]
        return None

    def count(self) -> int:
        return len(self._hist)
