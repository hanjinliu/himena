from __future__ import annotations

from qtpy import QtWidgets as QtW
from qtpy.QtCore import Qt, Signal
from himena_builtins.qt.widgets._table_components._base import QTableBase
from himena.qt._qlineedit import QIntLineEdit
from himena.qt._utils import qsignal_blocker


class QSelectionRangeEdit(QtW.QGroupBox):
    sliceChanged = Signal(object)

    def __init__(
        self,
        table: QTableBase | None = None,
        parent: QtW.QWidget | None = None,
    ):
        super().__init__(parent)
        self.setStyleSheet("QSelectionRangeEdit {margin: 0px;}")
        self._qtable: QTableBase | None = None
        self.setLayout(QtW.QHBoxLayout())
        self.setContentsMargins(0, 0, 0, 0)
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setAlignment(Qt.AlignmentFlag.AlignRight)
        inner = QtW.QWidget()
        self.layout().addWidget(inner)
        layout = QtW.QHBoxLayout()
        layout.setContentsMargins(8, 0, 8, 0)
        layout.setSpacing(0)
        inner.setLayout(layout)
        self._r_start = _int_line_edit("Row starting index", self._rstart_changed)
        self._r_stop = _int_line_edit("Row stopping index", self._rstop_changed)
        self._c_start = _int_line_edit("Column starting index", self._cstart_changed)
        self._c_stop = _int_line_edit("Column stopping index", self._cstop_changed)
        self._r_colon = _label(":")
        self._c_colon = _label(":")
        rbox = _hbox(self._r_start, self._r_colon, self._r_stop)
        cbox = _hbox(self._c_start, self._c_colon, self._c_stop)

        layout.addWidget(QtW.QLabel("Select ("))
        layout.addWidget(rbox)
        layout.addWidget(_label(", "))
        layout.addWidget(cbox)
        layout.addWidget(QtW.QLabel(")"))

        if table is not None:
            self.connect_table(table)
        self.sliceChanged.connect(self._slice_changed)
        self.setMaximumWidth(150)

    def connect_table(self, table: QTableBase):
        if self._qtable is not None:
            self._qtable._selection_model.moved.disconnect(self._selection_changed)
        self._qtable = table
        self._qtable._selection_model.moved.connect(self._selection_changed)
        self.setSlice(((0, 1), (0, 1)))
        self._selection_changed()

    def _int_gt(self, s: str, default: int) -> int:
        if s.strip() == "":
            return default
        return max(int(s), default)

    def _int_lt(self, s: str, default: int) -> int:
        if s.strip() == "":
            return default
        return min(int(s), default)

    def _selection_changed(self):
        if self._qtable is None:
            return
        sels = self._qtable._selection_model.ranges
        if len(sels) == 0:
            return
        rsl, csl = sels[-1]
        self.setSlice(((rsl.start, rsl.stop), (csl.start, csl.stop)))

    def _slice_changed(self, sl: tuple[tuple[int, int], tuple[int, int]]):
        if self._qtable is None:
            return
        rsl, csl = sl
        self._qtable._selection_model.set_ranges([(slice(*rsl), slice(*csl))])
        idx = rsl[0] - 1, csl[0] - 1
        self._qtable._selection_model.current_index = idx
        index = self._qtable.model().index(*idx)
        self._qtable.setCurrentIndex(index)
        return None

    def slice(self) -> tuple[tuple[int, int], tuple[int, int]]:
        if self._qtable is None:
            return ((0, 1), (0, 1))
        rsl = (
            self._int_gt(self._r_start.text(), 0),
            self._int_lt(self._r_stop.text(), self._qtable.model().rowCount()),
        )
        csl = (
            self._int_gt(self._c_start.text(), 0),
            self._int_lt(self._c_stop.text(), self._qtable.model().columnCount()),
        )
        return rsl, csl

    def setSlice(self, sl: tuple[tuple[int, int], tuple[int, int]]):
        rsl, csl = sl
        rstart, rstop = rsl
        cstart, cstop = csl
        with qsignal_blocker(self):
            self._r_start.setText(str(rstart))
            self._r_stop.setText(str(rstop))
            self._c_start.setText(str(cstart))
            self._c_stop.setText(str(cstop))
        if rstart is not None and rstop is not None and rstop == rstart + 1:
            self._r_stop.hide()
            self._r_colon.hide()
        else:
            self._r_stop.show()
            self._r_colon.show()
        if cstart is not None and cstop is not None and cstop == cstart + 1:
            self._c_stop.hide()
            self._c_colon.hide()
        else:
            self._c_stop.show()
            self._c_colon.show()
        return None

    def _rstart_changed(self, txt: str):
        rstop = self._r_stop.text()
        if txt and rstop:
            if not self._r_stop.isVisible() or int(rstop) <= int(txt):
                self._r_stop.setText(str(int(txt) + 1))
            return self.sliceChanged.emit(self.slice())

    def _rstop_changed(self, txt: str):
        rstart = self._r_start.text()
        if txt and rstart and int(rstart) >= int(txt):
            int_rstop = int(txt)
            if int_rstop > 1:
                self._r_start.setText(str(int_rstop - 1))
            else:
                self._r_start.setText("0")
                self._r_stop.setText("1")
        return self.sliceChanged.emit(self.slice())

    def _cstart_changed(self, txt: str):
        cstop = self._c_stop.text()
        if txt and cstop:
            if not self._c_stop.isVisible() or int(cstop) <= int(txt):
                self._c_stop.setText(str(int(txt) + 1))
            return self.sliceChanged.emit(self.slice())

    def _cstop_changed(self, txt: str):
        cstart = self._c_start.text()
        if txt and cstart and int(cstart) >= int(txt):
            int_cstop = int(txt)
            if int_cstop > 1:
                self._c_start.setText(str(int_cstop - 1))
            else:
                self._c_start.setText("0")
                self._c_stop.setText("1")
        return self.sliceChanged.emit(self.slice())


def _label(text: str):
    label = QtW.QLabel(text)
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    label.setFixedWidth(8)
    return label


def _int_line_edit(tooltip: str, text_changed_callback) -> QIntLineEdit:
    out = QIntLineEdit()
    out.setObjectName("TableIndex")
    out.setToolTip(tooltip)
    out.setAlignment(Qt.AlignmentFlag.AlignRight)
    out.textChanged.connect(text_changed_callback)
    return out


def _hbox(*widgets: QtW.QWidget) -> QtW.QWidget:
    box = QtW.QWidget()
    layout = QtW.QHBoxLayout(box)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(0)
    for widget in widgets:
        layout.addWidget(widget)
    box.setFixedWidth(42)
    return box
