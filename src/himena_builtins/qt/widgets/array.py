from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, cast

from qtpy import QtGui, QtCore, QtWidgets as QtW
from qtpy.QtCore import Qt
import numpy as np

from himena._data_wrappers import ArrayWrapper, wrap_array
from himena.consts import StandardType, MonospaceFontFamily
from himena.standards.model_meta import ArrayMeta
from himena.types import WidgetDataModel
from himena.plugins import validate_protocol
from himena_builtins.qt.widgets._table_components import (
    QTableBase,
    QSelectionRangeEdit,
    format_table_value,
)


_LOGGER = logging.getLogger(__name__)


def _is_structured(arr: np.ndarray) -> bool:
    return isinstance(arr.dtype, (np.void, np.dtypes.VoidDType))


class QArrayModel(QtCore.QAbstractTableModel):
    """Table model for data frame."""

    def __init__(self, arr: np.ndarray, parent=None):
        super().__init__(parent)
        self._arr_slice = arr  # 2D
        self._slice: tuple[int, ...] = ()
        if arr.dtype.names is None:
            if arr.ndim != 2:
                raise ValueError("Only 2D array is supported.")
            self._dtype = np.dtype(arr.dtype)
            self._nrows, self._ncols = arr.shape
            self._get_dtype = self._get_dtype_nonstructured
            self._get_item = self._get_item_nonstructured
        else:
            if arr.ndim != 1 or not _is_structured(arr):
                raise ValueError(
                    f"Only 1D structured array is supported (got {arr.ndim}D array "
                    f"with dtype {arr.dtype!r})."
                )
            self._dtype = arr.dtype
            self._nrows, self._ncols = arr.shape[0], len(arr.dtype.names)
            self._get_dtype = self._get_dtype_structured
            self._get_item = self._get_item_structured

    def _is_structured(self) -> bool:
        return isinstance(self._dtype, np.void)

    def _get_dtype_nonstructured(self, r: int, c: int) -> np.dtype:
        return self._dtype

    def _get_dtype_structured(self, r: int, c: int) -> np.dtype:
        return self._dtype.fields[self._dtype.names[c]][0]

    def _get_item_nonstructured(self, r: int, c: int) -> Any:
        return self._arr_slice[r, c]

    def _get_item_structured(self, r: int, c: int) -> Any:
        return self._arr_slice[r][self._dtype.names[c]]

    def rowCount(self, parent=None):
        return self._nrows

    def columnCount(self, parent=None):
        return self._ncols

    def data(
        self,
        index: QtCore.QModelIndex,
        role: Qt.ItemDataRole = Qt.ItemDataRole.DisplayRole,
    ):
        if not index.isValid():
            return QtCore.QVariant()
        if role == Qt.ItemDataRole.TextAlignmentRole:
            return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        if role == Qt.ItemDataRole.ToolTipRole:
            r, c = index.row(), index.column()
            array_indices = ", ".join(str(i) for i in self._slice + (r, c))
            return f"A[{array_indices}] = {self._get_item(r, c)}"
        if role != Qt.ItemDataRole.DisplayRole:
            return QtCore.QVariant()
        r, c = index.row(), index.column()
        if r < self.rowCount() and c < self.columnCount():
            value = self._get_item(r, c)
            text = format_table_value(value, self._get_dtype(r, c).kind)
            return text
        return QtCore.QVariant()

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ):
        if role == Qt.ItemDataRole.DisplayRole:
            if (
                _is_structured(self._arr_slice)
                and orientation == Qt.Orientation.Horizontal
            ):
                return self._dtype.names[section]
            return str(section)
        elif role == Qt.ItemDataRole.ToolTipRole:
            if (
                _is_structured(self._arr_slice)
                and orientation == Qt.Orientation.Horizontal
            ):
                name = self._dtype.names[section]
                return f"{name} (dtype: {self._dtype.fields[name][0]})"
            return None


class QArraySliceView(QTableBase):
    """A table widget for viewing 2-D array."""

    def __init__(self):
        super().__init__()
        self.horizontalHeader().setFixedHeight(18)
        self.verticalHeader().setDefaultSectionSize(20)
        self.horizontalHeader().setDefaultSectionSize(55)
        self.setModel(QArrayModel(np.zeros((0, 0))))
        self.setFont(QtGui.QFont(MonospaceFontFamily, 10))

    def update_width_by_dtype(self):
        kind = self.model()._dtype.kind
        depth = self.model()._dtype.itemsize
        if kind in "ui":
            self._update_width(min(depth * 40, 55))
        elif kind == "f":
            self._update_width(min(depth * 40, 55))
        elif kind == "c":
            self._update_width(min(depth * 40 + 8, 55))
        else:
            self._update_width(55)

    def _update_width(self, width: int):
        header = self.horizontalHeader()
        header.setDefaultSectionSize(width)
        # header.resizeSections(QtW.QHeaderView.ResizeMode.Fixed)
        for i in range(header.count()):
            header.resizeSection(i, width)

    def set_array(self, arr: np.ndarray, slice_):
        if arr.ndim != 2:
            raise ValueError("Only 2D array is supported.")
        self.model()._arr_slice = arr
        self.model()._slice = slice_
        self.update()

    def keyPressEvent(self, e: QtGui.QKeyEvent) -> None:
        if e.matches(QtGui.QKeySequence.StandardKey.Copy):
            return self.copy_data()
        if (
            e.modifiers() & Qt.KeyboardModifier.ControlModifier
            and e.key() == QtCore.Qt.Key.Key_F
        ):
            self._find_string()
            return
        return super().keyPressEvent(e)

    def copy_data(self):
        from io import StringIO

        sels = self._selection_model.ranges
        if len(sels) > 1:
            _LOGGER.warning("Multiple selections.")
            return
        buf = StringIO()
        np.savetxt(
            buf,
            self.model()._arr_slice[sels[0]],
            delimiter=",",
            fmt=dtype_to_fmt(self.model()._dtype),
        )
        clipboard = QtGui.QGuiApplication.clipboard()
        clipboard.setText(buf.getvalue())

    if TYPE_CHECKING:

        def model(self) -> QArrayModel: ...


def dtype_to_fmt(dtype: np.dtype) -> str:
    """Choose a proper format string for the dtype to convert to text."""
    if dtype.kind == "fc":
        dtype = cast(np.number, dtype)
        s = 1 if dtype.kind == "f" else 2
        if dtype.itemsize / s == 2:
            # 16bit has 10bit (~10^3) fraction
            return "%.4e"
        if dtype.itemsize / s == 4:
            # 32bit has 23bit (~10^7) fraction
            return "%.8e"
        if dtype.itemsize / s == 8:
            # 64bit has 52bit (~10^15) fraction
            return "%.16e"
        if dtype.itemsize / s == 16:
            # 128bit has 112bit (~10^33) fraction
            return "%.34e"
        raise RuntimeError(f"Unsupported float dtype: {dtype}")

    if dtype.kind in "iub":
        return "%d"
    return "%s"


class QArrayView(QtW.QWidget):
    """A widget for viewing n-D array."""

    __himena_widget_id__ = "builtins:QArrayView"
    __himena_display_name__ = "Bulit-in Array Viewer"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._table = QArraySliceView()
        layout = QtW.QVBoxLayout(self)

        self._spinbox_group = QtW.QWidget()
        group_layout = QtW.QHBoxLayout(self._spinbox_group)
        group_layout.setContentsMargins(1, 1, 1, 1)
        group_layout.setAlignment(Qt.AlignmentFlag.AlignRight)
        group_layout.addWidget(QtW.QLabel("Slice:"))

        layout.addWidget(self._table)
        layout.addWidget(self._spinbox_group)
        self._spinboxes: list[QtW.QSpinBox] = []
        self._arr: ArrayWrapper | None = None
        self._control: QArrayViewControl | None = None
        self._model_type = StandardType.ARRAY

    def update_spinbox_for_shape(self, shape: tuple[int, ...]):
        nspin = len(self._spinboxes)
        if nspin < len(shape) - 2:
            for _i in range(nspin, len(shape) - 2):
                self._make_spinbox(shape[_i])

        for i, sb in enumerate(self._spinboxes):
            if i < len(shape) - 2:
                sb.setVisible(True)
                _max = shape[i] - 1
                if sb.value() > _max:
                    sb.setValue(_max)
                sb.setRange(0, _max)
            else:
                self._spinbox_group.layout().removeWidget(sb)
                sb.deleteLater()
                self._spinboxes.remove(sb)

        self._spinbox_group.setVisible(len(shape) > 2)

    def _spinbox_changed(self):
        arr = self._arr
        if arr is None:
            return
        sl = self._get_slice()
        arr = self._arr.get_slice(sl)
        if arr.ndim < 2:
            arr = arr.reshape(-1, 1)
        self._table.set_array(arr, sl)

    def _get_slice(self) -> tuple[int | slice, ...]:
        if self._arr.ndim < 2:
            return (slice(None),)
        return tuple(sb.value() for sb in self._spinboxes) + (slice(None), slice(None))

    def _make_spinbox(self, max_value: int):
        spinbox = QtW.QSpinBox()
        self._spinbox_group.layout().addWidget(spinbox)
        spinbox.setRange(0, max_value - 1)
        spinbox.valueChanged.connect(self._spinbox_changed)
        self._spinboxes.append(spinbox)

    @validate_protocol
    def update_model(self, model: WidgetDataModel):
        arr = wrap_array(model.value)
        self._arr = arr
        self.update_spinbox_for_shape(arr.shape)
        if arr.ndim < 2:
            arr_slice = arr.get_slice(())
            if _is_structured(arr_slice):
                self._table.setModel(QArrayModel(arr_slice))
            else:
                self._table.setModel(QArrayModel(arr_slice.reshape(-1, 1)))
        else:
            sl = self._get_slice()
            self._table.setModel(QArrayModel(arr.get_slice(sl)))

        if self._control is None:
            self._control = QArrayViewControl(self._table)
        self._control.update_for_array(self._arr)
        self._table.update_width_by_dtype()
        self._model_type = model.type
        self.update()
        return None

    @validate_protocol
    def to_model(self) -> WidgetDataModel[list[list[Any]]]:
        selections = []
        for (r0, r1), (c0, c1) in self._table._get_selections():
            selections.append((slice(r0, r1), slice(c0, c1)))
        self._spinbox_group
        return WidgetDataModel(
            value=self._arr.arr,
            type=self.model_type(),
            extension_default=".npy",
            metadata=ArrayMeta(
                current_indices=self._get_slice(),
                selections=selections,
            ),
        )

    @validate_protocol
    def model_type(self) -> str:
        return self._model_type

    @validate_protocol
    def is_modified(self) -> bool:
        return False

    @validate_protocol
    def control_widget(self):
        return self._control


_R_CENTER = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter


class QArrayViewControl(QtW.QWidget):
    def __init__(self, view: QArrayView):
        super().__init__()
        layout = QtW.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(_R_CENTER)
        self._label = QtW.QLabel("")
        self._label.setAlignment(_R_CENTER)
        layout.addWidget(self._label)
        layout.addWidget(QSelectionRangeEdit(view))

    def update_for_array(self, arr: ArrayWrapper):
        _type_desc = arr.model_type()
        if not _is_structured(arr):
            self._label.setText(f"{_type_desc} {arr.shape!r} {arr.dtype}")
        else:
            self._label.setText(f"{_type_desc} {arr.shape!r} (structured)")
        return None
