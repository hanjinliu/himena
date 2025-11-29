from __future__ import annotations

from abc import ABC, abstractmethod
import numpy as np


class TableProxy(ABC):
    """Abstract base class for table proxies."""

    @abstractmethod
    def map(self, index: int) -> int:
        """Map the given index to another index."""


class IdentityProxy(TableProxy):
    def map(self, index: int) -> int:
        return index


class SortProxy(TableProxy):
    def __init__(self, index: int, mapping: np.ndarray, ascending: bool = True):
        self._index = index
        self._mapping = mapping
        self._ascending = ascending

    @property
    def index(self) -> int:
        return self._index

    @property
    def ascending(self) -> bool:
        return self._ascending

    @classmethod
    def from_array(cls, index: int, arr: np.ndarray) -> SortProxy:
        arr1d = arr[:, index]
        sorted_indices = np.argsort(arr1d)
        return cls(index, sorted_indices)

    def map(self, index: int) -> int:
        return self._mapping[index]

    def switch_ascending(self) -> SortProxy:
        mapping = self._mapping[::-1]
        ascending = not self._ascending
        return SortProxy(self._index, mapping, ascending)
