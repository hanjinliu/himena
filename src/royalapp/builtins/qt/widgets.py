from __future__ import annotations

from typing import TYPE_CHECKING
from qtpy import QtWidgets as QtW
from qtpy import QtGui, QtCore
from superqt import QLabeledSlider
from royalapp.consts import StandardTypes
from royalapp.types import WidgetDataModel
from royalapp.qt import register_frontend_widget
from royalapp.qt._qt_consts import MonospaceFontFamily

if TYPE_CHECKING:
    import numpy as np
    from numpy.typing import NDArray


def register_default_widget_types() -> None:
    """Register default widget types."""
    register_frontend_widget("text", QDefaultTextEdit, override=False)
    register_frontend_widget(StandardTypes.TEXT, QDefaultTextEdit, override=False)
    register_frontend_widget("table", QDefaultTableWidget, override=False)
    register_frontend_widget(StandardTypes.TABLE, QDefaultTableWidget, override=False)
    register_frontend_widget("image", QDefaultImageView, override=False)
    register_frontend_widget(StandardTypes.IMAGE, QDefaultImageView, override=False)


class QDefaultTextEdit(QtW.QPlainTextEdit):
    def __init__(self, file_path):
        super().__init__()
        self.setWordWrapMode(QtGui.QTextOption.WrapMode.NoWrap)
        self.setFont(QtGui.QFont(MonospaceFontFamily))
        self._file_path = file_path
        self._modified = False

        @self.textChanged.connect
        def _():
            self._modified = True

    @classmethod
    def from_model(cls, model: WidgetDataModel) -> QDefaultTextEdit:
        self = cls(model.source)
        self.setPlainText(model.value)
        if model.source is not None:
            self.setObjectName(model.source.name)
        return self

    def to_model(self) -> WidgetDataModel:
        return WidgetDataModel(
            value=self.toPlainText(),
            type=StandardTypes.TEXT,
            source=self._file_path,
        )

    def is_modified(self) -> bool:
        return self._modified


class QDefaultTableWidget(QtW.QTableWidget):
    def __init__(self, file_path):
        super().__init__()
        self._file_path = file_path
        self.horizontalHeader().hide()
        self._modified = False

        @self.itemChanged.connect
        def _():
            self._modified = True

    @classmethod
    def from_model(cls, model: WidgetDataModel) -> QDefaultTableWidget:
        import numpy as np

        self = cls(model.source)
        table = np.asarray(model.value, dtype=str)
        self.setRowCount(table.shape[0])
        self.setColumnCount(table.shape[1])
        for i in range(self.rowCount()):
            for j in range(self.columnCount()):
                self.setItem(i, j, QtW.QTableWidgetItem(table[i, j]))
            self.setRowHeight(i, 22)
        if model.source is not None:
            self.setObjectName(model.source.name)
        return self

    def to_model(self) -> WidgetDataModel:
        return WidgetDataModel(
            value=self._to_list(
                slice(0, self.rowCount()), slice(0, self.columnCount())
            ),
            type=StandardTypes.TABLE,
            source=self._file_path,
        )

    def is_modified(self) -> bool:
        return self._modified

    def _to_list(self, rsl: slice, csl: slice) -> list[list[str]]:
        values: list[list[str]] = []
        for r in range(rsl.start, rsl.stop):
            cells: list[str] = []
            for c in range(csl.start, csl.stop):
                item = self.item(r, c)
                if item is not None:
                    cells.append(item.text())
                else:
                    cells.append("")
            values.append(cells)
        return values

    def _copy_to_clipboard(self):
        selranges = self.selectedRanges()
        if not selranges:
            return
        if len(selranges) > 1:
            return

        # copy first selection range
        sel = selranges[0]
        values = self._to_list(
            slice(sel.topRow(), sel.bottomRow() + 1),
            slice(sel.leftColumn(), sel.rightColumn() + 1),
        )
        if values:
            string = "\n".join(["\t".join(cells) for cells in values])
            QtW.QApplication.clipboard().setText(string)

    def _paste_from_clipboard(self):
        sel_idx = self.selectedIndexes()
        if not sel_idx:
            return
        text = QtW.QApplication.clipboard().text()
        if not text:
            return

        # paste in the text
        row0, col0 = sel_idx[0].row(), sel_idx[0].column()
        data = [line.split("\t") for line in text.splitlines()]
        if (row0 + len(data)) > self.rowCount():
            self.setRowCount(row0 + len(data))
        if data and (col0 + len(data[0])) > self.columnCount():
            self.setColumnCount(col0 + len(data[0]))
        for r, line in enumerate(data):
            for c, cell in enumerate(line):
                try:
                    self.item(row0 + r, col0 + c).setText(str(cell))
                except AttributeError:
                    self.setItem(row0 + r, col0 + c, QtW.QTableWidgetItem(str(cell)))

        # select what was just pasted
        selrange = QtW.QTableWidgetSelectionRange(row0, col0, row0 + r, col0 + c)
        self.clearSelection()
        self.setRangeSelected(selrange, True)

    def _delete_selection(self):
        for item in self.selectedItems():
            item.setText("")

    def keyPressEvent(self, e: QtGui.QKeyEvent):
        _Ctrl = QtCore.Qt.KeyboardModifier.ControlModifier
        if e.modifiers() & _Ctrl and e.key() == QtCore.Qt.Key.Key_C:
            return self._copy_to_clipboard()
        if e.modifiers() & _Ctrl and e.key() == QtCore.Qt.Key.Key_V:
            return self._paste_from_clipboard()
        if e.modifiers() & _Ctrl and e.key() == QtCore.Qt.Key.Key_X:
            self._copy_to_clipboard()
            return self._delete_selection()
        if e.key() in (QtCore.Qt.Key.Key_Delete, QtCore.Qt.Key.Key_Backspace):
            return self._delete_selection()
        return super().keyPressEvent(e)


class _QImageLabel(QtW.QLabel):
    def __init__(self, val):
        super().__init__()
        self.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.setSizePolicy(
            QtW.QSizePolicy.Policy.Expanding, QtW.QSizePolicy.Policy.Expanding
        )
        self.set_array(val)

    def set_array(self, val: NDArray[np.uint8]):
        import numpy as np

        if val.ndim == 2:
            val = np.stack(
                [val] * 3 + [np.full(val.shape, 255, dtype=np.uint8)], axis=2
            )
        image = QtGui.QImage(
            val, val.shape[1], val.shape[0], QtGui.QImage.Format.Format_RGBA8888
        )
        self._pixmap_orig = QtGui.QPixmap.fromImage(image)
        self._update_pixmap()

    def _update_pixmap(self):
        sz = self.size()
        self.setPixmap(
            self._pixmap_orig.scaled(
                sz,
                QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                QtCore.Qt.TransformationMode.SmoothTransformation,
            )
        )

    def resizeEvent(self, ev: QtGui.QResizeEvent) -> None:
        self._update_pixmap()


class QDefaultImageView(QtW.QWidget):
    def __init__(self, model: WidgetDataModel[NDArray[np.uint8]]):
        super().__init__()
        layout = QtW.QVBoxLayout()
        ndim = model.value.ndim - 2
        if model.value.shape[-1] in (3, 4):
            ndim -= 1
        sl_0 = (0,) * ndim
        self._image_label = _QImageLabel(self.as_image_array(model.value[sl_0]))
        layout.addWidget(self._image_label)

        self._sliders: list[QtW.QSlider] = []
        for i in range(ndim):
            slider = QLabeledSlider(QtCore.Qt.Orientation.Horizontal)
            self._sliders.append(slider)
            layout.addWidget(slider, alignment=QtCore.Qt.AlignmentFlag.AlignBottom)
            slider.setRange(0, model.value.shape[i] - 1)
            slider.valueChanged.connect(self._slider_changed)
        self.setLayout(layout)
        self._model = model

    def _slider_changed(self):
        sl = tuple(sl.value() for sl in self._sliders)
        arr = self.as_image_array(self._model.value[sl])
        self._image_label.set_array(arr)

    @classmethod
    def from_model(cls, model: WidgetDataModel) -> QDefaultImageView:
        self = cls(model)
        if model.source is not None:
            self.setObjectName(model.source.name)
        return self

    def to_model(self) -> WidgetDataModel:
        return WidgetDataModel(
            value=self._model.value,
            type=self._model.type,
            source=self._model.source,
        )

    def as_image_array(self, arr: np.ndarray) -> NDArray[np.uint8]:
        import numpy as np

        if arr.dtype == "uint8":
            arr0 = arr
        elif arr.dtype == "uint16":
            arr0 = (arr / 256).astype("uint8")
        elif arr.dtype.kind == "f":
            min_ = arr.min()
            max_ = arr.max()
            if min_ < max_:
                arr0 = ((arr - min_) / (max_ - min_) * 255).astype("uint8")
            else:
                arr0 = np.zeros(arr.shape, dtype=np.uint8)
        else:
            raise ValueError(f"Unsupported data type: {arr.dtype}")
        return np.ascontiguousarray(arr0)


register_default_widget_types()
del register_default_widget_types
