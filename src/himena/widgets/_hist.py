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

    def get_from_last(self, num: int) -> _T | None:
        if len(self._hist) >= num:
            return self._hist[-num]
        return None
