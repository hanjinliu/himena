from __future__ import annotations

from typing import TYPE_CHECKING, Callable, NamedTuple
from himena.consts import StandardType
import numpy as np
from numpy.typing import NDArray

if TYPE_CHECKING:
    from himena.types import WidgetDataModel
    from himena.widgets import SubWindow

    # Single 2D selection in the form of ((row start, row stop), (col start, col stop))
    # We should avoid using slice because it is not serializable.
    SelectionType = tuple[tuple[int, int], tuple[int, int]]


class NamedArray(NamedTuple):
    name: str | None
    array: NDArray[np.number]


def model_to_xy_arrays(
    model: WidgetDataModel,
    x: SelectionType | None,
    y: SelectionType | None,
    *,
    allow_empty_x: bool = True,
    allow_multiple_y: bool = True,
    same_size: bool = True,
) -> tuple[NamedArray, list[NamedArray]]:
    from himena._data_wrappers import wrap_dataframe
    from himena.standards.model_meta import ExcelMeta

    if x is None and not allow_empty_x:
        raise ValueError("The x value must be given.")
    if y is None:
        raise ValueError("The y value must be given.")
    if model.is_subtype_of(StandardType.TABLE):
        (xlabel, xarr), ys = table_to_xy_arrays(
            model.value, x, y, allow_multiple_y=allow_multiple_y, same_size=same_size
        )
    elif model.is_subtype_of(StandardType.DATAFRAME):
        df = wrap_dataframe(model.value)
        column_names = df.column_names()[y[1][0] : y[1][1]]
        rows = slice(y[0][0], y[0][1])
        ys = [
            NamedArray(cname, df.column_to_array(cname)[rows]) for cname in column_names
        ]
        if x is None:
            xarr = np.arange(ys[0][1].size)
            xlabel = None
        else:
            column_names_x = df.column_names()[x[1][0] : x[1][1]]
            if len(column_names_x) != 1:
                raise ValueError("x must not be more than one column.")
            xarr = df.column_to_array(column_names_x[0])
            xlabel = column_names_x[0]
    elif model.is_subtype_of(StandardType.EXCEL):
        if not isinstance(meta := model.metadata, ExcelMeta):
            raise ValueError("Must be a ExcelMeta")
        table = model.value[meta.current_sheet]
        (xlabel, xarr), ys = table_to_xy_arrays(
            table, x, y, allow_multiple_y=allow_multiple_y, same_size=same_size
        )
    else:
        raise ValueError(f"Table-like data expected, but got model type {model.type!r}")
    return NamedArray(xlabel, xarr), ys


def table_to_xy_arrays(
    value: np.ndarray,
    x: SelectionType | None,
    y: SelectionType,
    *,
    allow_empty_x: bool = True,
    allow_multiple_y: bool = True,
    same_size: bool = True,
) -> tuple[NamedArray, list[tuple[NamedArray]]]:
    if x is None and not allow_empty_x:
        raise ValueError("The x value must be given.")
    ysl = slice(y[0][0], y[0][1]), slice(y[1][0], y[1][1])
    parser = TableValueParser.from_array(value[ysl])
    if x is None:
        xarr = np.arange(parser.n_samples, dtype=np.float64)
        xlabel = None
    else:
        xsl = slice(x[0][0], x[0][1]), slice(x[1][0], x[1][1])
        xlabel, xarr = parser.norm_x_value(value[xsl], same_size=same_size)
    if not allow_multiple_y and parser.n_components > 1:
        raise ValueError("Multiple Y values are not allowed.")
    return NamedArray(xlabel, xarr), parser.named_arrays


class TableValueParser:
    def __init__(
        self,
        label_and_values: list[NamedArray],
        is_column_vector: bool = True,
    ):
        self._label_and_values = label_and_values
        self._is_column_vector = is_column_vector

    @property
    def named_arrays(self) -> list[NamedArray]:
        return self._label_and_values

    @classmethod
    def from_columns(cls, value: np.ndarray) -> TableValueParser:
        nr, nc = value.shape
        if nr == 1:
            return cls(
                [NamedArray(None, value[:, i].astype(np.float64)) for i in range(nc)]
            )
        try:
            value[0, :].astype(np.float64)  # try to cast to float
        except ValueError:
            # The first row is not numerical. Use it as labels.
            return cls(
                [
                    NamedArray(str(value[0, i]), value[1:, i].astype(np.float64))
                    for i in range(nc)
                ]
            )
        else:
            return cls(
                [NamedArray(None, value[:, i].astype(np.float64)) for i in range(nc)]
            )

    @classmethod
    def from_rows(cls, value: np.ndarray) -> TableValueParser:
        self = cls.from_columns(value.T)
        self._is_column_vector = False
        return self

    @classmethod
    def from_array(cls, value: np.ndarray) -> TableValueParser:
        try:
            return cls.from_columns(value)
        except ValueError:
            return cls.from_rows(value)

    @property
    def n_components(self) -> int:
        return len(self._label_and_values)

    @property
    def n_samples(self) -> int:
        return self._label_and_values[0][1].size

    def norm_x_value(self, arr: np.ndarray, same_size: bool = True) -> NamedArray:
        # check if the first value is a label
        if self._is_column_vector and arr.shape[1] != 1:
            raise ValueError("The X values must be a 1D column vector.")
        if not self._is_column_vector and arr.shape[0] != 1:
            raise ValueError("The X values must be a 1D row vector.")
        arr = arr.ravel()
        try:
            arr[:1].astype(np.float64)
        except ValueError:
            label, arr_number = str(arr[0]), arr[1:].astype(np.float64)
        else:
            label, arr_number = None, arr.astype(np.float64)
        if same_size and arr_number.size != self.n_samples:
            raise ValueError("The number of X values must be the same as the Y values.")
        return NamedArray(label, arr_number)


def range_getter(win: SubWindow) -> Callable[[], tuple[SelectionType, SelectionType]]:
    """The getter function for SelectionEdit"""
    from himena.standards.model_meta import TableMeta

    def _getter():
        model = win.to_model()
        types = [StandardType.TABLE, StandardType.DATAFRAME, StandardType.EXCEL]
        if model.type not in types:
            raise ValueError(f"Cannot plot model of type {model.type!r}")
        if not isinstance(meta := model.metadata, TableMeta):
            raise ValueError("Excel must have TableMeta as the additional data.")
        if len(meta.selections) == 0:
            raise ValueError(f"No selection found in window {model.title!r}")
        elif len(meta.selections) > 1:
            raise ValueError(f"More than one selection found in window {model.title!r}")
        sel = meta.selections[0]
        rindices, cindices = sel
        _assert_tuple_of_ints(rindices)
        _assert_tuple_of_ints(cindices)
        return rindices, cindices

    return _getter


def _assert_tuple_of_ints(value: tuple[int, int]) -> None:
    if not isinstance(value, tuple) or len(value) != 2:
        raise ValueError("Must be a tuple of two integers.")
    if not all(isinstance(v, int) for v in value):
        raise ValueError("Must be a tuple of two integers.")
