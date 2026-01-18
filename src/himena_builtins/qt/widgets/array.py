from __future__ import annotations

from io import StringIO
import logging
from typing import TYPE_CHECKING, Any, cast
from dataclasses import dataclass
from qtpy import QtGui, QtCore, QtWidgets as QtW
from qtpy.QtCore import Qt
import numpy as np

from himena.data_wrappers import ArrayWrapper, wrap_array
from himena.consts import StandardType, MonospaceFontFamily
from himena.standards.model_meta import ArrayMeta
from himena.types import WidgetDataModel
from himena.plugins import validate_protocol
from himena.utils.collections import UndoRedoStack
from himena.utils.misc import is_structured
from himena_builtins.qt.widgets._table_components import (
    QTableBase,
    Editability,
    QSelectionRangeEdit,
    format_table_value,
    FLAGS,
    parse_string,
)

if TYPE_CHECKING:
    from himena.widgets import MainWindow
    from himena_builtins.qt.widgets._table_components import SelectionModel


_LOGGER = logging.getLogger(__name__)


class QArrayModel(QtCore.QAbstractTableModel):
    """Table model for data frame."""

    def __init__(self, arr: np.ndarray, parent: QArrayView | None = None):
        super().__init__(parent)
        self._arr_slice = arr  # 2D
        self._slice: tuple[int, ...] = ()
        if not is_structured(arr):
            if arr.ndim != 2:
                raise ValueError("Only 2D array is supported.")
            self._dtype = np.dtype(arr.dtype)
            self._nrows, self._ncols = arr.shape
            self._get_dtype = self._get_dtype_nonstructured
            self._get_item = self._get_item_nonstructured
        else:
            if arr.ndim != 1 or not is_structured(arr):
                raise ValueError(
                    f"Only 1D structured array is supported (got {arr.ndim}D array "
                    f"with dtype {arr.dtype!r})."
                )
            self._dtype = arr.dtype
            self._nrows, self._ncols = arr.shape[0], len(arr.dtype.names)
            self._get_dtype = self._get_dtype_structured
            self._get_item = self._get_item_structured
        self._is_original_array = True

    def _get_dtype_nonstructured(self, r: int, c: int) -> np.dtype:
        return self._dtype

    def _get_dtype_structured(self, r: int, c: int) -> np.dtype:
        return self._dtype.fields[self._dtype.names[c]][0]

    def _get_item_nonstructured(self, r: int, c: int) -> Any:
        return self._arr_slice[r, c]

    def _get_item_structured(self, r: int, c: int) -> Any:
        return self._arr_slice[r][self._dtype.names[c]]

    def flags(self, index: QtCore.QModelIndex) -> Qt.ItemFlag:
        return FLAGS

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
            return None
        elif role == Qt.ItemDataRole.TextAlignmentRole:
            r, c = index.row(), index.column()
            if r < self.rowCount() and c < self.columnCount():
                if self._get_dtype(r, c).kind in "iuf":
                    return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                else:
                    return Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        elif role == Qt.ItemDataRole.ToolTipRole:
            r, c = index.row(), index.column()
            array_indices = ", ".join(str(i) for i in self._slice + (r, c))
            return f"A[{array_indices}] = {self._get_item(r, c)!r}"
        elif role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
            r, c = index.row(), index.column()
            if r < self.rowCount() and c < self.columnCount():
                value = self._get_item(r, c)
                if role == Qt.ItemDataRole.DisplayRole:
                    text = format_table_value(value, self._get_dtype(r, c).kind)
                else:
                    text = str(value)
                return text
        return None

    def setData(self, index: QtCore.QModelIndex, value: Any, role: int = ...) -> bool:
        if role == Qt.ItemDataRole.EditRole:
            self.parent()._table.set_string_input(index.row(), index.column(), value)
            return True
        return False

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ):
        if role == Qt.ItemDataRole.DisplayRole:
            if (
                is_structured(self._arr_slice)
                and orientation == Qt.Orientation.Horizontal
            ):
                return self._dtype.names[section]
            return str(section)
        elif role == Qt.ItemDataRole.ToolTipRole:
            if (
                is_structured(self._arr_slice)
                and orientation == Qt.Orientation.Horizontal
            ):
                name = self._dtype.names[section]
                return f"{name} (dtype: {self._dtype.fields[name][0]})"
            return None

    if TYPE_CHECKING:

        def parent(self) -> QArrayView: ...


class QArraySliceView(QTableBase):
    def __init__(self, ui, parent: QArrayView):
        super().__init__(ui, parent)
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
        for i in range(header.count()):
            header.resizeSection(i, width)

    def set_array(self, arr: np.ndarray, slice_):
        self.model()._arr_slice = arr
        self.model()._slice = slice_
        self.update()

    def set_string_input(self, r: int, c: int, value: str):
        view = self.parent()
        sl = view._get_indices() + (r, c)
        view.array_update(sl, value, record_undo=True)

    def _copy_data(self):
        sels = self._selection_model.ranges
        if len(sels) > 1:
            _LOGGER.warning("Multiple selections.")
            return
        sel = sels[0]
        arr_slice = self.model()._arr_slice
        buf = StringIO()
        if is_structured(arr_slice):
            fields = [
                arr_slice.dtype.names[i] for i in range(sel[1].start, sel[1].stop)
            ]
            arr_to_copy = arr_slice[sel[0]][fields]
        else:
            arr_to_copy = arr_slice[sel]
        fmt = dtype_to_fmt(self.model()._dtype)
        np.savetxt(
            buf,
            arr_to_copy,
            delimiter="\t",
            fmt=fmt,
        )
        clipboard = QtW.QApplication.clipboard()
        clipboard.setText(buf.getvalue().rstrip("\n"))

    def _paste_from_clipboard(self):
        text = QtW.QApplication.clipboard().text()
        if not text:
            return

        buf = StringIO(text)
        arr_paste = np.loadtxt(
            buf, dtype=np.dtypes.StringDType(), delimiter="\t", ndmin=2
        )
        # undo info
        rng = self._selection_model.get_single_range()
        if rng[0].stop - rng[0].start == 1 and rng[1].stop - rng[1].start == 1:
            # 1x1 selection can be pasted to any size
            rng = (
                slice(rng[0].start, rng[0].start + arr_paste.shape[0]),
                slice(rng[1].start, rng[1].start + arr_paste.shape[1]),
            )
        sl = self.parent()._get_indices() + rng
        _ud_old_data = self.parent()._arr.get_slice(sl).copy()

        self._paste_array(sl, arr_paste)

        # undo info
        _ud_new_data = arr_paste.copy()
        _action_edit = EditAction(_ud_old_data, _ud_new_data, sl)
        self.parent()._undo_stack.push(_action_edit)

        # select what was just pasted
        self._selection_model.set_ranges([rng])
        self.update()

    def _paste_array(self, sl, arr_paste: np.ndarray):
        arr_slice = self.model()._arr_slice
        arr = self.parent()._arr

        rng = self._selection_model.get_single_range()
        row0, col0 = rng[0].start, rng[1].start
        lr = max(arr_paste.shape[0], rng[0].stop - rng[0].start)
        lc = max(arr_paste.shape[1], rng[1].stop - rng[1].start)

        # expand the table if necessary
        if (row0 + lr) > arr_slice.shape[0] or (col0 + lc) > arr_slice.shape[1]:
            raise ValueError("Cannot paste outside of the array.")

        # paste the data
        if is_structured(arr):
            raise NotImplementedError("Structured array paste is not implemented.")
        else:
            arr[sl] = arr_paste
        self.parent()._spinbox_changed()

    def _make_context_menu(self):
        menu = QtW.QMenu(self)
        menu.addAction("Copy", self._copy_data)
        menu.addAction("Paste", self._paste_from_clipboard)
        return menu

    if TYPE_CHECKING:

        def model(self) -> QArrayModel: ...
        def parent(self) -> QArrayView: ...


class QArrayView(QtW.QWidget):
    """A widget for viewing n-D arrays.

    ## Basic Usage

    The 2D array sliced for the last dimensions (such as A[2, 1, :, :]) are shown in the
    table. "2D array" can be any numpy-like arrays, including `xarray.DataArray`,
    `dask.array.Array`, `cupy.ndarray`, etc. If the array is more than 2D, spinboxes are
    shown in the bottom of the widget to select the slice. Numpy structured arrays are
    also supported.

    ## Copying Data

    Selected range can be copied `Ctrl+C`. The copied data is in tab-separated format so
    that it can be pasted to spreadsheet softwares.

    ## Editing Data

    You can edit the data in the current slice of the array. Input text will be parsed
    to the dtype of the array.
    """

    __himena_widget_id__ = "builtins:QArrayView"
    __himena_display_name__ = "Bulit-in Array Viewer"

    def __init__(self, ui: MainWindow):
        super().__init__()
        self._table = QArraySliceView(ui, parent=self)
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
        self._undo_stack = UndoRedoStack[EditAction](size=20)
        self._axes = None

    @property
    def selection_model(self) -> SelectionModel:
        """The selection model of the array slice view."""
        return self._table.selection_model

    def set_indices(self, *indices):
        for sb, idx in zip(self._spinboxes, indices, strict=True):
            sb.setValue(idx)
        self._spinbox_changed()

    def _update_spinbox_for_shape(self, shape: tuple[int, ...], dims_shown: int = 2):
        nspin = len(self._spinboxes)
        # make insufficient spinboxes
        for _i in range(nspin, len(shape) - dims_shown):
            self._make_spinbox(shape[_i])

        for i, sb in enumerate(self._spinboxes):
            if i < len(shape) - dims_shown:
                sb.setVisible(True)
                _max = shape[i] - 1
                if sb.value() > _max:
                    sb.setValue(_max)
                sb.setRange(0, _max)
            else:
                self._spinbox_group.layout().removeWidget(sb)
                sb.deleteLater()
                self._spinboxes.remove(sb)

        self._spinbox_group.setVisible(len(shape) > dims_shown)

    def _spinbox_changed(self):
        arr = self._arr
        if arr is None:
            return
        sl = self._get_slice()
        arr = self._arr.get_slice(sl)
        if arr.ndim < 2 and not is_structured(self._arr.arr):
            arr = arr.reshape(-1, 1)
        self._table.set_array(arr, sl)

    def _get_slice(self) -> tuple[int | slice, ...]:
        if self._arr.ndim < 2:
            return (slice(None),)
        arr_structured = is_structured(self._arr.arr)
        if arr_structured:
            last_sl = (slice(None),)
        else:
            last_sl = (slice(None), slice(None))
        return self._get_indices() + last_sl

    def _get_indices(self) -> tuple[int, ...]:
        return tuple(sb.value() for sb in self._spinboxes)

    def _make_spinbox(self, max_value: int):
        spinbox = QtW.QSpinBox()
        self._spinbox_group.layout().addWidget(spinbox)
        spinbox.setRange(0, max_value - 1)
        spinbox.valueChanged.connect(self._spinbox_changed)
        self._spinboxes.append(spinbox)

    @validate_protocol
    def update_model(self, model: WidgetDataModel):
        was_none = self._arr is None
        arr = wrap_array(model.value)
        self._arr = arr
        arr_structured = is_structured(arr.arr)
        self._update_spinbox_for_shape(arr.shape, dims_shown=1 if arr_structured else 2)
        if arr.ndim < 2:
            arr_slice = arr.get_slice(())
            if is_structured(arr_slice):
                self._table.setModel(QArrayModel(arr_slice, self))
            else:
                self._table.setModel(QArrayModel(arr_slice.reshape(-1, 1), self))
        else:
            sl = self._get_slice()
            self._table.setModel(QArrayModel(arr.get_slice(sl), self))

        self.control_widget().update_for_array(self)
        if was_none:
            self._table.update_width_by_dtype()
        if isinstance(meta := model.metadata, ArrayMeta):
            if meta.selections:  # if has selections, they need updating
                self.selection_model.clear()
            for (r0, r1), (c0, c1) in meta.selections:
                self.selection_model.append((slice(r0, r1), slice(c0, c1)))
            self._axes = meta.axes

        self._model_type = model.type
        self._modified_override = None
        self.update()
        return None

    @validate_protocol
    def to_model(self) -> WidgetDataModel[list[list[Any]]]:
        # NOTE: if this model is passed to another widget and modified in this widget,
        # the other dataframe will be modified as well. To avoid this, we need to reset
        # the copy-on-write state of this array.
        self._table.model()._is_original_array = True
        current_indices = tuple(
            None if isinstance(sl, slice) else sl for sl in self._get_slice()
        )
        return WidgetDataModel(
            value=self._arr.arr,
            type=self.model_type(),
            extension_default=".npy",
            metadata=ArrayMeta(
                axes=self._axes,
                current_indices=current_indices,
                selections=self._table._get_selections(),
            ),
        )

    @validate_protocol
    def model_type(self) -> str:
        return self._model_type

    @validate_protocol
    def size_hint(self):
        return 320, 280

    @validate_protocol
    def is_modified(self) -> bool:
        if self._modified_override is not None:
            return self._modified_override
        return self._undo_stack.undoable()

    @validate_protocol
    def set_modified(self, value: bool) -> None:
        self._modified_override = value

    @validate_protocol
    def is_editable(self) -> bool:
        return self._table.editTriggers() == Editability.TRUE

    @validate_protocol
    def set_editable(self, value: bool) -> None:
        if value:
            trig = Editability.TRUE
        else:
            trig = Editability.FALSE
        self._table.setEditTriggers(trig)

    @validate_protocol
    def control_widget(self) -> QArrayViewControl:
        if self._control is None:
            self._control = QArrayViewControl()
        return self._control

    def array_update(
        self,
        sl,
        value: Any,
        *,
        record_undo: bool = True,
    ) -> None:
        """Update the data at the given index."""
        _ud_old_data = self._arr[sl]
        if isinstance(_ud_old_data, ArrayWrapper):
            _ud_old_data = _ud_old_data.copy()
        if self._table.model()._is_original_array:
            self._arr = self._arr.copy()
            self._table.model()._is_original_array = False
            self._spinbox_changed()  # update slice
        if isinstance(value, str):
            self._arr[sl] = parse_string(value, self._arr.dtype.kind)
        else:
            # called in undo/redo
            self._arr[sl] = value
        _ud_new_data = self._arr[sl]
        _action = EditAction(_ud_old_data, _ud_new_data, sl)
        if record_undo:
            self._undo_stack.push(_action)

    def undo(self):
        if action := self._undo_stack.undo():
            action.invert().apply(self)
            self.update()

    def redo(self):
        if action := self._undo_stack.redo():
            action.apply(self)
            self.update()

    def keyPressEvent(self, e: QtGui.QKeyEvent) -> None:
        _Ctrl = QtCore.Qt.KeyboardModifier.ControlModifier
        _mod = e.modifiers()
        _key = e.key()
        if _mod & _Ctrl and _key == QtCore.Qt.Key.Key_Z:
            self.undo()
            return
        elif _mod & _Ctrl and _key == QtCore.Qt.Key.Key_Y:
            self.redo()
            return
        if _mod & _Ctrl and _key == QtCore.Qt.Key.Key_C:
            return self._table._copy_data()
        if _mod & _Ctrl and _key == QtCore.Qt.Key.Key_V:
            return self._table._paste_from_clipboard()
        if _mod & _Ctrl and _key == QtCore.Qt.Key.Key_F:
            self._table._find_string()
            return
        return super().keyPressEvent(e)

    def setFocus(self) -> None:
        self._table.setFocus()


_R_CENTER = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter


class QArrayViewControl(QtW.QWidget):
    def __init__(self):
        super().__init__()
        layout = QtW.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(_R_CENTER)
        self._label = QtW.QLabel("")
        self._label.setAlignment(_R_CENTER)
        layout.addWidget(self._label)
        self._selection_range = QSelectionRangeEdit()
        layout.addWidget(self._selection_range)

    def update_for_array(self, widget: QArrayView):
        if widget is None:
            return None
        _type_desc = widget.model_type()
        arr = widget._arr
        if arr is None:
            self._label.setText("No data available.")
            return None
        if not is_structured(arr):
            self._label.setText(f"{_type_desc} {arr.shape!r} {arr.dtype}")
        else:
            ncols = len(arr.dtype.names)
            self._label.setText(f"{_type_desc} {arr.shape!r} x {ncols} fields")
        self._selection_range.connect_table(widget._table)
        return None


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


@dataclass
class EditAction:
    old: Any
    new: Any
    index: Any

    def invert(self) -> EditAction:
        return EditAction(self.new, self.old, self.index)

    def apply(self, table: QArrayView):
        return table.array_update(self.index, self.new, record_undo=False)
