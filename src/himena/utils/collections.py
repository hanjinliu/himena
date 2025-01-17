from __future__ import annotations

from typing import (
    Generic,
    Hashable,
    Iterable,
    Iterator,
    MutableSet,
    Sequence,
    TypeVar,
)

_T = TypeVar("_T", bound=Hashable)


class OrderedSet(MutableSet[_T]):
    """A set that maintains the order of the elements."""

    def __init__(self, iterable: Iterable[_T] = ()):
        self._dict: dict[_T, None] = dict.fromkeys(iterable)

    def __contains__(self, other) -> bool:
        return other in self._dict

    def __iter__(self) -> Iterator[_T]:
        yield from self._dict

    def __len__(self) -> int:
        return len(self._dict)

    def add(self, value: _T) -> None:
        self._dict[value] = None

    def discard(self, value: _T) -> None:
        self._dict.pop(value, None)

    def update(self, other: Iterable[_T]) -> None:
        for value in other:
            self.add(value)


class FrozenList(Sequence[_T]):
    """A immutable list."""

    def __init__(self, iterable: Iterable[_T]):
        self._list = list(iterable)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self._list!r})"

    def __getitem__(self, index: int) -> _T:
        return self._list[index]

    def __len__(self) -> int:
        return len(self._list)

    def __iter__(self) -> Iterator[_T]:
        yield from self._list


class UndoRedoStack(Generic[_T]):
    """A simple undo/redo stack to store the history."""

    def __init__(self, size: int = 10):
        self._stack_undo: list[_T] = []
        self._stack_redo: list[_T] = []
        self._size = size

    def push(self, value: _T):
        """Push a new value."""
        self._stack_undo.append(value)
        self._stack_redo.clear()
        if len(self._stack_undo) > self._size:
            self._stack_undo.pop(0)

    def undo(self) -> _T | None:
        """Undo and return the value. None if empty."""
        if len(self._stack_undo) == 0:
            return None
        value = self._stack_undo.pop()
        self._stack_redo.append(value)
        return value

    def redo(self) -> _T | None:
        """Redo and return the value. None if empty."""
        if len(self._stack_redo) == 0:
            return None
        value = self._stack_redo.pop()
        self._stack_undo.append(value)
        return value

    def undoable(self) -> bool:
        """If undo is possible."""
        return len(self._stack_undo) > 0

    def redoable(self) -> bool:
        """If redo is possible."""
        return len(self._stack_redo) > 0

    def clear(self):
        """Clear the stack."""
        self._stack_undo.clear()
        self._stack_redo.clear()
