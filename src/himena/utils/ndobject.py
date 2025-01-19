from __future__ import annotations

import numpy as np
from numpy.typing import NDArray
from typing import Callable, Iterator, TYPE_CHECKING, Generic, TypeVar
from dataclasses import dataclass, field

if TYPE_CHECKING:
    from typing import Self

_T = TypeVar("_T")
_U = TypeVar("_U")


def _item_factory():
    return np.empty((0,), dtype=np.object_)


def _indices_factory():
    return np.empty((0, 0), dtype=np.int32)


@dataclass
class NDObjectCollection(Generic[_T]):
    """List of nd objects, with useful methods."""

    items: NDArray[np.object_] = field(default_factory=_item_factory)
    indices: NDArray[np.int32] = field(default_factory=_indices_factory)
    axis_names: list[str] = field(default_factory=list)

    def __post_init__(self):
        if not isinstance(self.items, np.ndarray):
            self.items = np.asarray(self.items, dtype=np.object_)
        if self.items.ndim != 1:
            raise ValueError(
                f"Items must be a 1D array, got {self.items} ({self.items.ndim}D)."
            )
        if self.indices.shape[1] == 0:
            self.indices = np.empty((len(self.items), 0), dtype=np.int32)
        elif self.indices.shape[0] != len(self.items):
            raise ValueError("Indices must have the same length as items.")
        if self.indices.shape[0] == 0:
            self.indices = np.empty((0, len(self.axis_names)), dtype=np.int32)

    def set_axis_names(self, names: list[str]):
        """Update the axis names and coerce array shapes."""
        if self.indices.shape[0] == 0:
            self.indices = np.empty((0, len(names)), dtype=np.uint32)
        else:
            if self.indices.shape[1] != len(names):
                raise ValueError(
                    f"Expected {self.indices.shape[1]} axis names, got {len(names)}"
                )
        self.axis_names = names

    def coerce_dimensions(self, target_axis_names: list[str]) -> Self:
        """Reformat the collection to match the target axis names."""
        if self.axis_names == target_axis_names:
            return self
        columns = []
        for aname in target_axis_names:
            if aname in self.axis_names:
                index = self.axis_names.index(aname)
                columns.append(self.indices[:, index])
            else:
                columns.append(-np.ones(len(self.items), dtype=np.int32))
        indices = np.column_stack(columns)
        return self.__class__(
            items=self.items,
            indices=indices,
            axis_names=target_axis_names,
        )

    def mask_by_indices(self, key: tuple[int, ...]) -> NDArray[np.bool_] | None:
        """Binary mask for the given indices (None if nothing to mask out)."""
        if self.indices is None:
            raise ValueError("Indices are not set.")
        if len(self.axis_names) != len(key):
            raise ValueError(
                f"Expected {self.indices.shape[1]} indices, got {len(key)}"
            )
        ok = None
        for column_index, value in enumerate(key):
            column = self.indices[:, column_index]
            contains = np.logical_or(column == value, column < 0)
            if ok is None:
                ok = contains
            else:
                ok = ok & contains
        return ok

    def filter_by_indices(self, key: tuple[int, ...]) -> Self:
        ok = self.mask_by_indices(key)
        if ok is None:
            return self.__class__(
                items=self.items,
                indices=self.indices,
                axis_names=self.axis_names,
            )
        else:
            return self.__class__(
                items=self.items[ok],
                indices=self.indices[ok],
                axis_names=self.axis_names,
            )

    def filter_by_selection(self, selection: NDArray[np.bool_] | list[int]) -> Self:
        return self.__class__(
            items=self.items[selection],
            indices=self.indices[selection],
            axis_names=self.axis_names,
        )

    def add_item(self, indices, item: _T) -> None:
        """Add item at the given indice"""
        self.items = np.append(self.items, item)
        indices = np.atleast_2d(indices)
        self.indices = np.append(self.indices, indices, axis=0)

    def extend(self, other: Self) -> None:
        if len(self) > 0:
            if self.axis_names != other.axis_names:
                raise ValueError("Axis names must match.")
        if len(self) == 0:
            self.items = other.items.copy()
            self.indices = other.indices.copy()
        else:
            self.items = np.concatenate([self.items, other.items], axis=0)
            self.indices = np.concatenate([self.indices, other.indices], axis=0)
        return None

    def pop(self, index: int) -> _T:
        item = self.items[index]
        self.items = np.delete(self.items, index)
        self.indices = np.delete(self.indices, index)
        return item

    def clear(self) -> None:
        self.items = _item_factory()
        self.indices = _indices_factory()

    def copy(self) -> Self:
        return self.__class__(
            items=self.items.copy(),
            indices=self.indices.copy(),
            axis_names=self.axis_names.copy(),
        )

    def __getitem__(self, key: int) -> _T:
        return self.items[key]

    def __iter__(self) -> Iterator[_T]:
        return iter(self.items)

    def iter_with_indices(self) -> Iterator[tuple[tuple[int, ...], _T]]:
        for indices, item in zip(self.indices, self.items):
            yield tuple(indices), item

    def __len__(self) -> int:
        return len(self.items)

    def take_axis(self, axis: int, index: int):
        axis_name = self.axis_names[axis]
        column = self.indices[:, axis]
        ok = np.logical_or(column == index, column < 0)
        items = self.items[ok]
        indices = self.indices[ok]
        axis_names = [name for name in self.axis_names if name != axis_name]
        return self.__class__(
            items=items,
            indices=indices,
            axis_names=axis_names,
        )

    def project(self, axis: int):
        axis_name = self.axis_names[axis]
        items = self.items
        indices = self.indices
        axis_names = [name for name in self.axis_names if name != axis_name]
        return self.__class__(
            items=items,
            indices=indices,
            axis_names=axis_names,
        )

    def map_elements(
        self,
        func: Callable[[_T], _U],
        into: type[NDObjectCollection] | None = None,
    ) -> NDObjectCollection[_U]:
        if into is None:
            into = self.__class__
        return into(
            items=[func(item) for item in self.items],
            indices=self.indices,
            axis_names=self.axis_names,
        )
