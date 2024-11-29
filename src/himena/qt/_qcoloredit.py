from __future__ import annotations
from qtpy import QtWidgets as QtW, QtGui
from qtpy.QtCore import Qt, Signal


# modified from napari/_qt/widgets/qt_color_swatch.py
class QColorSwatch(QtW.QFrame):
    colorChanged = Signal(QtGui.QColor)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFrameStyle(QtW.QFrame.Shape.Panel | QtW.QFrame.Shadow.Sunken)
        self._qcolor: QtGui.QColor = QtGui.QColor(255, 255, 255, 255)
        self.colorChanged.connect(self._update_swatch_style)
        self.setMinimumWidth(40)

    @property
    def rgba(self) -> tuple[int, int, int, int]:
        """Get RBGA tuple from QColor."""
        return self._qcolor.getRgb()

    def heightForWidth(self, w: int) -> int:
        return w

    def _update_swatch_style(self, color: QtGui.QColor) -> None:
        rgba = f'rgba({",".join(str(x) for x in color.getRgb())})'
        return self.setStyleSheet("QColorSwatch {background-color: " + rgba + ";}")

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:
        """Show QColorPopup picker when the user clicks on the swatch."""
        if event.button() == Qt.MouseButton.LeftButton:
            dlg = QtW.QColorDialog(self._qcolor, self)
            dlg.setOptions(QtW.QColorDialog.ColorDialogOption.ShowAlphaChannel)
            ok = dlg.exec_()
            if ok:
                self.setQColor(dlg.selectedColor())

    def qColor(self) -> QtGui.QColor:
        return self._qcolor

    def setQColor(self, color: QtGui.QColor) -> None:
        old_color = self._qcolor
        self._qcolor = color
        if self._qcolor.getRgb() != old_color.getRgb():
            self.colorChanged.emit(color)


class QColorLineEdit(QtW.QLineEdit):
    colorChanged = Signal()

    def __init__(self, parent: QtW.QWidget | None = None):
        super().__init__(parent)
        self._qcolor = QtGui.QColor(255, 255, 255, 255)
        self.editingFinished.connect(self._emit_color_changed)

    def qColor(self) -> QtGui.QColor:
        """Get color as QtGui.QColor object"""
        return self._qcolor

    def setQColor(self, color: QtGui.QColor):
        self._qcolor = color
        text = color.name()
        self.setText(text)

    def _emit_color_changed(self):
        text = self.text()
        try:
            qcolor = QtGui.QColor(text)
        except ValueError:
            self.setQColor(self._qcolor)
        else:
            if self._qcolor.getRgb() != qcolor.getRgb():
                self._qcolor = qcolor
                self.colorChanged.emit()


class QColorEdit(QtW.QWidget):
    colorChanged = Signal(tuple)

    def __init__(self, parent=None):
        super().__init__(parent)
        _layout = QtW.QHBoxLayout(self)
        self._color_swatch = QColorSwatch(self)
        self._line_edit = QColorLineEdit(self)
        _layout.addWidget(self._color_swatch)
        _layout.addWidget(self._line_edit)
        _layout.setContentsMargins(0, 0, 0, 0)

        self._color_swatch.colorChanged.connect(self._on_swatch_changed)
        self._line_edit.colorChanged.connect(self._on_line_edit_edited)

    def color(self) -> QtGui.QColor:
        """Return the current color."""
        return self._color_swatch._qcolor

    def rgba(self) -> tuple[float, float, float, float]:
        return self.color().getRgbF()

    def setColor(self, color: QtGui.QColor):
        """Set value as the current color."""
        self._line_edit.setQColor(color)
        self._color_swatch.setQColor(color)

    def setRgba(self, rgba):
        qcolor = QtGui.QColor.fromRgbF(*rgba)
        self.setColor(qcolor)

    def _on_line_edit_edited(self):
        self._line_edit.blockSignals(True)
        qcolor = self._line_edit.qColor()
        self._color_swatch.setQColor(qcolor)
        self._line_edit.blockSignals(False)
        self.colorChanged.emit(qcolor.getRgb())

    def _on_swatch_changed(self, qcolor: QtGui.QColor):
        self._color_swatch.blockSignals(True)
        try:
            self._line_edit.setQColor(qcolor)
        finally:
            self._color_swatch.blockSignals(False)
        self.colorChanged.emit(qcolor.getRgb())
