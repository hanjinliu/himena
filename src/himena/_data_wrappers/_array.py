# This file is mostly copied from pyapp-kit/ndv
# BSD-3-Clause License
# https://github.com/pyapp-kit/ndv

from __future__ import annotations

import sys
from abc import abstractmethod
from collections.abc import Hashable, Sequence
from typing import (
    TYPE_CHECKING,
    Generic,
    TypeVar,
)

import numpy as np

if TYPE_CHECKING:
    from typing import Any, Protocol, TypeAlias, TypeGuard

    import dask.array as da
    import numpy.typing as npt
    import pyopencl.array as cl_array
    import sparse
    import tensorstore as ts
    import xarray as xr
    import zarr
    from torch._tensor import Tensor
    import cupy

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
    """Interface for wrapping different array-like data types.

    `DataWrapper.create` is a factory method that returns a DataWrapper instance
    for the given data type. If your datastore type is not supported, you may implement
    a new DataWrapper subclass to handle your data type.  To do this, import and
    subclass DataWrapper, and (minimally) implement the supports and isel methods.
    Ensure that your class is imported before the DataWrapper.create method is called,
    and it will be automatically detected and used to wrap your data.
    """

    def __init__(self, data: ArrayT) -> None:
        self._arr = data

    @property
    def arr(self) -> ArrayT:
        return self._arr

    @abstractmethod
    def get_slice(self, sl: tuple[int, ...]) -> np.ndarray:
        raise NotImplementedError

    @property
    @abstractmethod
    def dtype(self) -> np.dtype:
        """Return the data type of the array."""

    @property
    @abstractmethod
    def shape(self) -> tuple[int, ...]:
        """Return the shape of the array."""
        shape = getattr(self._arr, "shape", None)
        if not isinstance(shape, Sequence) or not all(
            isinstance(x, int) for x in shape
        ):
            raise NotImplementedError(f"Cannot determine sizes for {type(self._arr)}")
        dims = range(len(shape))
        return {dim: int(size) for dim, size in zip(dims, shape)}

    @property
    def ndim(self) -> int:
        return len(self.shape)

    def model_type(self) -> str:
        typ = type(self._arr)
        return f"{typ.__module__}.{typ.__name__}"


class XarrayWrapper(ArrayWrapper["xr.DataArray"]):
    """Wrapper for xarray DataArray objects."""

    def get_slice(self, sl: tuple[int, ...]) -> np.ndarray:
        return self._arr.isel(dict(enumerate(sl))).values

    @property
    def dtype(self) -> np.dtype:
        return self._arr.dtype

    @property
    def shape(self) -> tuple[int, ...]:
        return self._arr.shape


class TensorstoreWrapper(ArrayWrapper["ts.TensorStore"]):
    """Wrapper for tensorstore.TensorStore objects."""

    def __init__(self, data: Any) -> None:
        super().__init__(data)
        import json

        import tensorstore as ts

        self._ts = ts

        spec = self.arr.spec().to_json()
        labels: Sequence[Hashable] | None = None
        if (tform := spec.get("transform")) and ("input_labels" in tform):
            labels = [str(x) for x in tform["input_labels"]]
        elif (
            str(spec.get("driver")).startswith("zarr")
            and (zattrs := self.arr.kvstore.read(".zattrs").result().value)
            and isinstance((zattr_dict := json.loads(zattrs)), dict)
            and "_ARRAY_DIMENSIONS" in zattr_dict
        ):
            labels = zattr_dict["_ARRAY_DIMENSIONS"]

        if isinstance(labels, Sequence) and len(labels) == len(self._data.domain):
            self._data = self.arr[ts.d[:].label[self._labels]]

    def get_slice(self, sl: tuple[int, ...]) -> np.ndarray:
        return self._data[sl].read().result()

    @property
    def dtype(self) -> np.dtype:
        return np.dtype(self._data.domain.dtype)

    @property
    def shape(self) -> tuple[int, ...]:
        return self._data.domain.shape


class ArrayLikeWrapper(ArrayWrapper, Generic[ArrayT]):
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


class DaskWrapper(ArrayWrapper["da.Array"]):
    """Wrapper for dask array objects."""

    def get_slice(self, sl: tuple[int, ...]) -> np.ndarray:
        return self._arr[sl].compute()

    @property
    def dtype(self) -> np.dtype:
        return self._arr.dtype

    @property
    def shape(self) -> tuple[int, ...]:
        return self._arr.shape


class CLArrayWrapper(ArrayLikeWrapper["cl_array.Array"]):
    """Wrapper for pyopencl array objects."""

    @staticmethod
    def _asarray(data: cl_array.Array) -> np.ndarray:
        return np.asarray(data.get())


class SparseArrayWrapper(ArrayLikeWrapper["sparse.Array"]):
    @staticmethod
    def _asarray(data: sparse.COO) -> np.ndarray:
        return np.asarray(data.todense())


class TorchTensorWrapper(ArrayWrapper["torch.Tensor"]):
    """Wrapper for torch tensor objects."""

    def get_slice(self, sl: tuple[int, ...]) -> np.ndarray:
        return self.arr[sl].numpy(force=True)

    @property
    def dtype(self) -> np.dtype:
        return self.arr.dtype

    @property
    def shape(self) -> tuple[int, ...]:
        return self.arr.shape


class CupyArrayWrapper(ArrayLikeWrapper["cupy.ndarray"]):
    """Wrapper for cupy array objects."""

    @staticmethod
    def _asarray(data: cupy.ndarray) -> np.ndarray:
        return data.get()


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


def is_cl_array(data: Any) -> TypeGuard[cl_array.Array]:
    if _see_imported_module(data, "pyopencl"):
        import pyopencl.array as cl_array

        return isinstance(data, cl_array.Array)
    return False


def is_sparse(data: Any) -> TypeGuard[sparse.Array]:
    if _see_imported_module(data, "sparse"):
        import sparse

        return isinstance(data, sparse.Array)
    return False


def is_tensorstore(data: Any) -> TypeGuard[ts.TensorStore]:
    if _see_imported_module(data, "tensorstore"):
        import tensorstore as ts

        return isinstance(data, ts.TensorStore)
    return False


def is_torch_tensor(data: Any) -> TypeGuard[Tensor]:
    if _see_imported_module(data, "torch"):
        from torch._tensor import Tensor

        return isinstance(data, Tensor)
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


def is_cupy(data: Any) -> TypeGuard[cupy.ndarray]:
    if _see_imported_module(data, "cupy"):
        import cupy

        return isinstance(data, cupy.ndarray)
    return False


def wrap_array(arr: Any) -> ArrayWrapper:
    if is_numpy(arr):
        return ArrayLikeWrapper(arr)
    if is_dask(arr):
        return DaskWrapper(arr)
    if is_cl_array(arr):
        return CLArrayWrapper(arr)
    if is_sparse(arr):
        return SparseArrayWrapper(arr)
    if is_tensorstore(arr):
        return TensorstoreWrapper(arr)
    if is_torch_tensor(arr):
        return TorchTensorWrapper(arr)
    if is_xarray(arr):
        return XarrayWrapper(arr)
    if is_zarr(arr):
        return ArrayLikeWrapper(arr)
    if is_cupy(arr):
        return CupyArrayWrapper(arr)
    raise NotImplementedError(f"Unsupported array type: {type(arr)}")
