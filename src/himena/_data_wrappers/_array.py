# This file is mostly copied from pyapp-kit/ndv
# BSD-3-Clause License
# https://github.com/pyapp-kit/ndv

from __future__ import annotations

import sys
from abc import abstractmethod
from typing import (
    TYPE_CHECKING,
    Generic,
    TypeVar,
)

import numpy as np

if TYPE_CHECKING:
    from typing import Any, Protocol, TypeAlias, TypeGuard, Self

    import dask.array as da
    import numpy.typing as npt
    import xarray as xr
    import zarr

    _T_contra = TypeVar("_T_contra", contravariant=True)
    Index = int | slice

    class SupportsIndexing(Protocol):
        def __getitem__(self, key: Index | tuple[Index, ...]) -> npt.ArrayLike: ...
        @property
        def shape(self) -> tuple[int, ...]: ...

    class SupportsDunderLT(Protocol[_T_contra]):
        def __lt__(self, other: _T_contra, /) -> bool: ...

    class SupportsDunderGT(Protocol[_T_contra]):
        def __gt__(self, other: _T_contra, /) -> bool: ...

    SupportsRichComparison: TypeAlias = SupportsDunderLT[Any] | SupportsDunderGT[Any]


ArrayT = TypeVar("ArrayT")


class ArrayWrapper(Generic[ArrayT]):
    """Interface for wrapping different array-like data types."""

    def __init__(self, data: ArrayT) -> None:
        self._arr = data

    def __getitem__(self, sl: tuple[Index, ...]) -> Self:
        return self.__class__(self._arr[sl])

    @property
    def arr(self) -> ArrayT:
        return self._arr

    @abstractmethod
    def get_slice(self, sl: tuple[int, ...]) -> np.ndarray:
        """Return a 2D slice of the array as a numpy array."""

    @property
    @abstractmethod
    def dtype(self) -> np.dtype:
        """Return the data type of the array."""

    @property
    @abstractmethod
    def shape(self) -> tuple[int, ...]:
        """Return the shape of the array."""

    @property
    def size(self) -> int:
        return np.prod(self.shape)

    def axis_names(self) -> list[str]:
        """Return the names of the axes."""
        return [f"axis-{i}" for i in range(self.ndim)]

    @property
    def ndim(self) -> int:
        return len(self.shape)

    def model_type(self) -> str:
        typ = type(self._arr)
        return f"{typ.__module__}.{typ.__name__}"


class XarrayWrapper(ArrayWrapper["xr.DataArray"]):
    """Wrapper for xarray DataArray objects."""

    def get_slice(self, sl: tuple[int, ...]) -> np.ndarray:
        return self._arr[sl].values

    @property
    def dtype(self) -> np.dtype:
        return self._arr.dtype

    @property
    def shape(self) -> tuple[int, ...]:
        return self._arr.shape

    def axis_names(self) -> list[str]:
        return [str(_a) for _a in self._arr.dims]


class ArrayLikeWrapper(ArrayWrapper[ArrayT]):
    """Wrapper for numpy duck array-like objects."""

    def get_slice(self, sl: tuple[int, ...]) -> np.ndarray:
        return self._asarray(self._arr[sl])

    @staticmethod
    def _asarray(data: ArrayT) -> np.ndarray:
        return np.asarray(data)

    @property
    def dtype(self) -> np.dtype:
        return self._arr.dtype

    @property
    def shape(self) -> tuple[int, ...]:
        return self._arr.shape


class DaskWrapper(ArrayLikeWrapper["da.Array"]):
    """Wrapper for dask array objects."""

    def get_slice(self, sl: tuple[int, ...]) -> np.ndarray:
        return self._arr[sl].compute()


class ZarrArrayWrapper(ArrayLikeWrapper["zarr.Array"]):
    """Wrapper for zarr array objects."""

    def __init__(self, data: Any) -> None:
        super().__init__(data)
        self._names = []
        if "_ARRAY_DIMENSIONS" in data.attrs:
            self._names = data.attrs["_ARRAY_DIMENSIONS"]
        else:
            self._names = list(range(data.ndim))

    def axis_names(self) -> list[str]:
        return [str(k) for k in self._names]


def _see_imported_module(arr: Any, module: str) -> bool:
    typ = type(arr)
    if module not in sys.modules or typ.__module__.split(".")[0] != module:
        return False
    return True


def is_numpy(data: Any) -> TypeGuard[np.ndarray]:
    return isinstance(data, np.ndarray)


def is_dask(data: Any) -> TypeGuard[da.Array]:
    if _see_imported_module(data, "dask"):
        import dask.array as da

        return isinstance(data, da.Array)
    return False


def is_xarray(data: Any) -> TypeGuard[xr.DataArray]:
    if _see_imported_module(data, "xarray"):
        import xarray as xr

        return isinstance(data, xr.DataArray)
    return False


def is_zarr(data: Any) -> TypeGuard[zarr.Array]:
    if _see_imported_module(data, "zarr"):
        import zarr

        return isinstance(data, zarr.Array)
    return False


def wrap_array(arr: Any) -> ArrayWrapper:
    if isinstance(arr, ArrayWrapper):
        return arr
    if is_numpy(arr):
        return ArrayLikeWrapper(arr)
    if is_dask(arr):
        return DaskWrapper(arr)
    if is_xarray(arr):
        return XarrayWrapper(arr)
    if is_zarr(arr):
        return ArrayLikeWrapper(arr)
    return ArrayLikeWrapper(arr)
