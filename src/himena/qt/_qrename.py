from __future__ import annotations

from qtpy import QtWidgets as QtW, QtCore, QtGui


class QRenameLineEdit(QtW.QLineEdit):
    rename_requested = QtCore.Signal(str)

    def __init__(self, parent: QtW.QWidget):
        super().__init__(parent)
        self.setHidden(True)

        @self.editingFinished.connect
        def _():
            if not self.isVisible():
                return
            self.setHidden(True)
            text = self.text()
            if text:
                self.rename_requested.emit(text)

    def keyPressEvent(self, a0: QtGui.QKeyEvent) -> None:
        if a0.key() == QtCore.Qt.Key.Key_Escape:
            self.setHidden(True)
        return super().keyPressEvent(a0)

    def focusOutEvent(self, a0: QtGui.QFocusEvent) -> None:
        self.setHidden(True)
        return super().focusOutEvent(a0)


class QTabRenameLineEdit(QRenameLineEdit):
    """LineEdit for renaming tab in QTabWidget."""

    def __init__(self, parent: QtW.QTabWidget, allow_duplicate: bool = True):
        super().__init__(parent)
        self._current_edit_index: int | None = None
        self._allow_duplicate = allow_duplicate

        @self.rename_requested.connect
        def _(new_name: str):
            if self._current_edit_index is None:
                return
            if not self._allow_duplicate:
                for i in range(self.parent().count()):
                    if i == self._current_edit_index:
                        continue
                    if self.parent().tabText(i) == new_name:
                        raise ValueError(f"Duplicate tab name: {new_name!r}")
            parent.setTabText(self._current_edit_index, new_name)

        parent.currentChanged.connect(self._hide_me)
        parent.tabBarDoubleClicked.connect(self.start_edit)

    def parent(self) -> QtW.QTabWidget:
        return super().parent()

    def keyPressEvent(self, a0: QtGui.QKeyEvent) -> None:
        if a0.key() == QtCore.Qt.Key.Key_Escape:
            self.setHidden(True)
        return super().keyPressEvent(a0)

    def showEvent(self, a0: QtGui.QShowEvent | None) -> None:
        self._current_edit_index = self.parent().currentIndex()
        return super().showEvent(a0)

    def _move_line_edit(
        self,
        rect: QtCore.QRect,
        text: str,
    ) -> QtW.QLineEdit:
        geometry = self.geometry()
        geometry.setWidth(rect.width())
        geometry.setHeight(rect.height())
        geometry.moveCenter(rect.center())
        geometry.adjust(4, 4, -2, -2)
        self.setGeometry(geometry)
        self.setText(text)
        self.setHidden(False)
        self.setFocus()
        self.selectAll()

    def _hide_me(self):
        self.setHidden(True)

    def start_edit(self, index: int):
        """Enter edit table name mode."""
        rect = self._tab_rect(index)
        self._current_edit_index = index
        self._move_line_edit(rect, self.parent().tabText(index))

    def _tab_rect(self, index: int) -> QtCore.QRect:
        """Get QRect of the tab at index."""
        tab_widget = self.parent()
        rect = tab_widget.tabBar().tabRect(index)
        return rect
