from __future__ import annotations

from abc import ABC, abstractmethod
from typing import overload
import numpy as np
from himena.data_wrappers import DataFrameWrapper


class TableProxy(ABC):
    """Abstract base class for table proxies."""

    @overload
    def map(self, index: int) -> int: ...
    @overload
    def map(self, index: np.ndarray) -> np.ndarray: ...

    @abstractmethod
    def map(self, index: int) -> int:
        """Map the given index to another index."""


class IdentityProxy(TableProxy):
    def map(self, index):
        return index


class SortProxy(TableProxy):
    def __init__(self, index: int, mapping: np.ndarray, ascending: bool = True):
        self._index = index
        self._mapping = mapping
        self._mapping_inv = None  # cache
        self._ascending = ascending

    @property
    def index(self) -> int:
        return self._index

    @property
    def ascending(self) -> bool:
        return self._ascending

    @classmethod
    def from_array(
        cls, index: int, arr: np.ndarray, ascending: bool = True
    ) -> SortProxy:
        arr1d = arr[:, index]
        sorted_indices = np.argsort(arr1d)
        return cls(index, sorted_indices, ascending=ascending)

    @classmethod
    def from_dataframe(
        cls,
        index: int,
        df: DataFrameWrapper,
        ascending: bool = True,
    ) -> SortProxy:
        column_name = df.column_names()[index]
        ser = df.column_to_array(column_name)
        sorted_indices = np.argsort(ser)
        return cls(index, sorted_indices, ascending=ascending)

    def map(self, index):
        if isinstance(index, np.ndarray):
            sl_in_range = index < self._mapping.size
            result = index.copy()
            result[sl_in_range] = self._mapping[index[sl_in_range]]
        else:
            if index >= self._mapping.size:
                result = index
            else:
                result = self._mapping[index]
        return result

    def switch_ascending(self) -> SortProxy:
        mapping = self._mapping[::-1]
        ascending = not self._ascending
        return SortProxy(self._index, mapping, ascending)
