from __future__ import annotations

from typing import Callable, Any
from qtpy import QtWidgets as QtW
from qtpy import QtCore
from qtpy.QtCore import Qt, Signal
from himena.model_meta import TableMeta
from himena.qt._qfinderwidget import QTableFinderWidget
from himena.qt._qlineedit import QIntLineEdit
from himena.qt._utils import qsignal_blocker


def _format_float(value, ndigits: int = 4) -> str:
    """convert string to int or float if possible"""
    if value is None:
        return "null"
    if 0.1 <= abs(value) < 10 ** (ndigits + 1) or value == 0:
        text = f"{value:.{ndigits}f}"
    else:
        text = f"{value:.{ndigits-1}e}"

    return text


def _format_int(value, ndigits: int = 4) -> str:
    if value is None:
        return "null"
    if 0.1 <= abs(value) < 10 ** (ndigits + 1) or value == 0:
        text = str(value)
    else:
        text = f"{value:.{ndigits-1}e}"

    return text


def _format_complex(value: complex, ndigits: int = 3) -> str:
    if value != value:  # nan
        text = "nan"
    elif 0.1 <= abs(value) < 10 ** (ndigits + 1) or value == 0:
        text = f"{value.real:.{ndigits}f}{value.imag:+.{ndigits}f}j"
    else:
        text = f"{value.real:.{ndigits-1}e}{value.imag:+.{ndigits-1}e}j"

    return text


def _format_datetime(value):
    return str(value)


_DEFAULT_FORMATTERS: dict[int, Callable[[Any], str]] = {
    "i": _format_int,
    "u": _format_int,
    "f": _format_float,
    "c": _format_complex,
    "t": _format_datetime,
}


def format_table_value(value: Any, fmt: str) -> str:
    return _DEFAULT_FORMATTERS.get(fmt, str)(value)


class QTableBase(QtW.QTableView):
    def __init__(self):
        super().__init__()
        self.horizontalHeader().setFixedHeight(18)
        self.verticalHeader().setDefaultSectionSize(22)
        self.horizontalHeader().setDefaultSectionSize(75)
        self._finder_widget: QTableFinderWidget | None = None

        # scroll by pixel
        self.setVerticalScrollMode(QtW.QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.setHorizontalScrollMode(QtW.QAbstractItemView.ScrollMode.ScrollPerPixel)
        # scroll bar policy
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        self.setSelectionMode(QtW.QAbstractItemView.SelectionMode.ExtendedSelection)

    def size_hint(self) -> tuple[int, int]:
        return 400, 300

    def is_editable(self) -> bool:
        return self.editTriggers() != QtW.QAbstractItemView.EditTrigger.NoEditTriggers

    def _find_string(self):
        if self._finder_widget is None:
            self._finder_widget = QTableFinderWidget(self)
        self._finder_widget.show()
        self._align_finder()

    def resizeEvent(self, event):
        if self._finder_widget is not None:
            self._align_finder()
        super().resizeEvent(event)

    def _align_finder(self):
        if fd := self._finder_widget:
            vbar = self.verticalScrollBar()
            if vbar.isVisible():
                fd.move(self.width() - fd.width() - vbar.width() - 3, 5)
            else:
                fd.move(self.width() - fd.width() - 3, 5)

    def _prep_table_meta(self) -> TableMeta:
        qselections = self.selectionModel().selection()
        selections = []
        for qselection in qselections:
            r = qselection.top(), qselection.bottom() + 1
            c = qselection.left(), qselection.right() + 1
            selections.append((r, c))
        index = self.currentIndex()
        return TableMeta(
            current_position=(index.row(), index.column()),
            selections=selections,
        )


class QSelectionRangeEdit(QtW.QGroupBox):
    sliceChanged = Signal(object)

    def __init__(self, table: QtW.QTableView, parent: QtW.QWidget | None = None):
        super().__init__(parent)
        self._qtable = table
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

        self._qtable.selectionModel().selectionChanged.connect(self._selection_changed)
        self.sliceChanged.connect(self._slice_changed)
        self.setSlice(((0, 1), (0, 1)))
        self.setMaximumWidth(190)

    def _int_gt(self, s: str, default: int) -> int:
        if s.strip() == "":
            return default
        return max(int(s), default)

    def _int_lt(self, s: str, default: int) -> int:
        if s.strip() == "":
            return default
        return min(int(s), default)

    def _selection_changed(self):
        sel = list(self._qtable.selectionModel().selection())
        if len(sel) == 0:
            return
        qselection = sel[-1]
        rstart = qselection.top()
        rstop = qselection.bottom() + 1
        cstart = qselection.left()
        cstop = qselection.right() + 1
        self.setSlice(((rstart, rstop), (cstart, cstop)))

    def _slice_changed(self, sl: tuple[tuple[int, int], tuple[int, int]]):
        rsl, csl = sl
        rstart, rstop = rsl
        cstart, cstop = csl
        self._qtable.selectionModel().clearSelection()
        qselection = QtCore.QItemSelection()
        qselection.select(
            self._qtable.model().index(rstart, cstart),
            self._qtable.model().index(rstop - 1, cstop - 1),
        )
        self._qtable.selectionModel().select(
            qselection,
            QtCore.QItemSelectionModel.SelectionFlag.Select,
        )
        index = self._qtable.model().index(rstop - 1, cstop - 1)
        self._qtable.setCurrentIndex(index)
        return None

    def slice(self) -> tuple[tuple[int, int], tuple[int, int]]:
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
    box.setFixedWidth(60)
    return box
