from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from qtpy import QtGui, QtCore, QtWidgets as QtW
from qtpy.QtCore import Qt
from himena._data_wrappers import ArrayWrapper, wrap_array
from himena.consts import StandardTypes
from himena.types import WidgetDataModel
from himena.builtins.qt.widgets._table_base import (
    QTableBase,
    QSelectionRangeEdit,
    format_table_value,
)


if TYPE_CHECKING:
    import numpy as np

_LOGGER = logging.getLogger(__name__)


class QArrayModel(QtCore.QAbstractTableModel):
    """Table model for data frame."""

    def __init__(self, arr: np.ndarray, parent=None):
        super().__init__(parent)
        self._arr_slice = arr  # 2D
        if arr.ndim != 2:
            raise ValueError("Only 2D array is supported.")
        self._dtype_kind = arr.dtype.kind

    def rowCount(self, parent=None):
        return self._arr_slice.shape[0]

    def columnCount(self, parent=None):
        return self._arr_slice.shape[1]

    def data(
        self,
        index: QtCore.QModelIndex,
        role: Qt.ItemDataRole = Qt.ItemDataRole.DisplayRole,
    ):
        if not index.isValid():
            return QtCore.QVariant()
        if role != Qt.ItemDataRole.DisplayRole:
            return QtCore.QVariant()
        r, c = index.row(), index.column()
        if r < self.rowCount() and c < self.columnCount():
            value = self._arr_slice[r, c]
            text = format_table_value(value, self._dtype_kind)
            return text
        return QtCore.QVariant()

    def flags(self, index):
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ):
        if role == Qt.ItemDataRole.DisplayRole:
            return str(section)


class QArraySliceView(QTableBase):
    """A table widget for viewing 2-D array."""

    def __init__(self):
        import numpy as np

        super().__init__()
        self.setModel(QArrayModel(np.zeros((0, 0))))
        self.setSelectionModel(QtCore.QItemSelectionModel(self.model()))

    def set_array(self, arr: np.ndarray):
        if arr.ndim != 2:
            raise ValueError("Only 2D array is supported.")
        self.model()._arr_slice = arr
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
        import numpy as np

        model = self.selectionModel()
        if not model.hasSelection():
            return
        qselections = self.selectionModel().selection()
        if len(qselections) > 1:
            _LOGGER.warning("Multiple selections.")
            return

        qsel = next(iter(qselections))
        r0, r1 = qsel.left(), qsel.right() + 1
        c0, c1 = qsel.top(), qsel.bottom() + 1
        buf = StringIO()
        np.savetxt(buf, self.model()._arr_slice[r0:r1, c0:c1], delimiter=",")
        clipboard = QtGui.QGuiApplication.clipboard()
        clipboard.setText(buf.getvalue())

    if TYPE_CHECKING:

        def model(self) -> QArrayModel: ...


class QDefaultArrayView(QtW.QWidget):
    """A widget for viewing n-D array."""

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

    def update_spinbox_for_shape(self, shape: tuple[int, ...]):
        if len(shape) < 3:
            for sb in self._spinboxes:
                sb.setVisible(False)
            return
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

    def _spinbox_changed(self):
        arr = self._arr
        if arr is None:
            return
        sl = self._get_slice()
        arr = self._arr.get_slice(sl)
        self._table.set_array(arr)

    def _get_slice(self) -> tuple[int, ...]:
        return tuple(sb.value() for sb in self._spinboxes)

    def _make_spinbox(self, max_value: int):
        spinbox = QtW.QSpinBox()
        self._spinbox_group.layout().addWidget(spinbox)
        spinbox.setRange(0, max_value - 1)
        spinbox.valueChanged.connect(self._spinbox_changed)
        self._spinboxes.append(spinbox)

    def update_model(self, model: WidgetDataModel):
        import numpy as np

        arr = wrap_array(model.value)
        self._arr = arr
        self.update_spinbox_for_shape(arr.shape)
        if arr.ndim < 2:
            self._table.setModel(QArrayModel(np.atleast_2d(arr.get_slice(()))))
        else:
            sl = self._get_slice()
            self._table.setModel(QArrayModel(arr.get_slice(sl)))
        self._table.setSelectionModel(QtCore.QItemSelectionModel(self._table.model()))

        if self._control is None:
            self._control = QArrayViewControl(self._table)
        self._control.update_for_array(self._arr)
        self.update()
        return None

    def to_model(self) -> WidgetDataModel[list[list[Any]]]:
        return WidgetDataModel(
            value=self._arr.arr,
            type=self.model_type(),
            extension_default=".npy",
        )

    def model_type(self) -> str:
        return f"{StandardTypes.ARRAY}.{self._arr.ndim}d"

    def is_modified(self) -> bool:
        return False

    def control_widget(self):
        return self._control


_R_CENTER = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter


class QArrayViewControl(QtW.QWidget):
    def __init__(self, view: QDefaultArrayView):
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
        self._label.setText(f"{_type_desc} {arr.shape!r} {arr.dtype}")
        return None
