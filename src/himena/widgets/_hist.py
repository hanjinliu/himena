from __future__ import annotations

from pathlib import Path
from typing import TypeVar, Generic

_T = TypeVar("_T")


class HistoryContainer(Generic[_T]):
    def __init__(self, max_size: int = 20):
        self._hist: list[_T] = []
        self._max_size = max_size

    def add(self, item: _T) -> None:
        """Add item to the history."""
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

    def pop_last(self) -> _T | None:
        """Pop the last item if exists."""
        if self._hist:
            return self._hist.pop()
        return None

    def len(self) -> int:
        return len(self._hist)

    def __len__(self) -> int:
        return self.len()


class FileDialogHistoryDict:
    """List of starting directories for file dialogs."""

    def __init__(self):
        self._dict: dict[str, Path] = {}

    def update(self, group_name: str, value: Path) -> None:
        self._dict[group_name] = value

    def get_path(self, group_name: str, filename: str | None = None) -> Path:
        d = self._dict.get(group_name, Path.cwd())
        if filename:
            return d / filename
        while not d.exists():
            d = d.parent
            if d == Path.home() or d == Path("."):
                break
        return d
