from __future__ import annotations

from qtpy import QtWidgets as QtW
from qtpy import QtGui, QtCore
from royalapp.consts import StandardTypes
from royalapp.types import WidgetDataModel
from royalapp.qt import register_frontend_widget
from royalapp.qt._qt_consts import MonospaceFontFamily


def register_default_widget_types() -> None:
    """Register default widget types."""
    register_frontend_widget("text", QDefaultTextEdit)
    register_frontend_widget(StandardTypes.TEXT, QDefaultTextEdit)
    register_frontend_widget("table", QDefaultTableWidget)
    register_frontend_widget(StandardTypes.TABLE, QDefaultTableWidget)
    register_frontend_widget("image", QDefaultImageView)
    register_frontend_widget(StandardTypes.IMAGE, QDefaultImageView)


class QDefaultTextEdit(QtW.QPlainTextEdit):
    def __init__(self, file_path):
        super().__init__()
        self.setWordWrapMode(QtGui.QTextOption.WrapMode.NoWrap)
        self.setFont(QtGui.QFont(MonospaceFontFamily))
        self._file_path = file_path

    # def _on_text_changed(self) -> None:
    #     self.setWindowModified(True)
    #     pass

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


class QDefaultTableWidget(QtW.QTableWidget):
    def __init__(self, file_path):
        super().__init__()
        self._file_path = file_path
        self.horizontalHeader().hide()

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


class QDefaultImageView(QtW.QLabel):
    def __init__(self, model: WidgetDataModel):
        import numpy as np

        super().__init__()
        val = np.ascontiguousarray(model.value)
        image = QtGui.QImage(
            val, val.shape[1], val.shape[0], QtGui.QImage.Format.Format_RGBA8888
        )
        self._pixmap_orig = QtGui.QPixmap.fromImage(image)
        self.setPixmap(self._pixmap_orig)
        self.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self._file_path = model.source

    @classmethod
    def from_model(cls, model: WidgetDataModel) -> QDefaultImageView:
        self = cls(model)
        if model.source is not None:
            self.setObjectName(model.source.name)
        return self

    def to_model(self) -> WidgetDataModel:
        from royalapp.qt._utils import qimage_to_ndarray

        arr = qimage_to_ndarray(self._pixmap_orig.toImage())
        return WidgetDataModel(
            value=arr,
            type=StandardTypes.IMAGE,
            source=self._file_path,
        )

    def resizeEvent(self, ev: QtGui.QResizeEvent) -> None:
        sz = self.size()
        self.setPixmap(
            self._pixmap_orig.scaled(
                sz,
                QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                QtCore.Qt.TransformationMode.SmoothTransformation,
            )
        )


register_default_widget_types()
del register_default_widget_types
