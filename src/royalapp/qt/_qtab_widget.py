from __future__ import annotations

from typing import TYPE_CHECKING, Iterator
from qtpy import QtWidgets as QtW
from qtpy import QtCore, QtGui
from royalapp.qt._qsub_window import QSubWindowArea


class QTabWidget(QtW.QTabWidget):
    newWindowActivated = QtCore.Signal()

    def __init__(self):
        super().__init__()
        self._line_edit = QRenameLineEdit(self)
        self._current_edit_index = None

        @self._line_edit.editingFinished.connect
        def _():
            if not self._line_edit.isVisible():
                return
            self._line_edit.setHidden(True)
            text = self._line_edit.text()
            if text and self._current_edit_index is not None:
                text = self._coerce_tab_name(text)
                self.setTabText(self._current_edit_index, text)

        self.setTabBarAutoHide(True)
        self.tabBar().setMovable(False)
        self.currentChanged.connect(self._on_current_changed)
        self.tabBarDoubleClicked.connect(self._start_editing_tab)

    def addTabArea(self, tab_name: str | None = None) -> QSubWindowArea:
        """
        Add a new tab with a sub-window area.

        Parameters
        ----------
        tab_name : str
            Name of the tab.
        """
        if tab_name is None:
            tab_name = "Tab"
        widget = QSubWindowArea()
        self.addTab(widget, self._coerce_tab_name(tab_name))
        widget.subWindowActivated.connect(self._emit_current_indices)
        return widget

    def iter_widgets(self) -> Iterator[QtW.QWidget]:
        """Iterate over all widgets in the tab widget."""
        for idx in self.count():
            area = self.widget(idx)
            yield from area.iter_widgets()

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        self._line_edit.setHidden(True)
        return super().mousePressEvent(event)

    def _coerce_tab_name(self, tab_name: str) -> str:
        """Coerce tab name to be unique."""
        existing = {self.tabText(i) for i in range(self.count())}
        tab_name_orig = tab_name
        count = 0
        while tab_name in existing:
            count += 1
            tab_name = f"{tab_name_orig}-{count}"
        return tab_name

    def _on_current_changed(self, index: int) -> None:
        if widget := self.widget(index):
            widget._reanchor_windows()
            self._emit_current_indices()
            self._line_edit.setHidden(True)

    def _current_indices(self) -> tuple[int, int]:
        if widget := self.currentWidget():
            if win := widget.currentSubWindow():
                return self.currentIndex(), widget.indexOf(win)
        return self.currentIndex(), -1

    def _emit_current_indices(self) -> None:
        self.newWindowActivated.emit()

    def _tab_rect(self, index: int) -> QtCore.QRect:
        """Get QRect of the tab at index."""
        rect = self.tabBar().tabRect(index)

        # NOTE: East/South tab returns wrong value (Bug in Qt?)
        if self.tabPosition() == QtW.QTabWidget.TabPosition.East:
            w = self.rect().width() - rect.width()
            rect.translate(w, 0)
        elif self.tabPosition() == QtW.QTabWidget.TabPosition.South:
            h = self.rect().height() - rect.height()
            rect.translate(0, h)

        return rect

    def _move_line_edit(
        self,
        rect: QtCore.QRect,
        text: str,
    ) -> QtW.QLineEdit:
        geometry = self._line_edit.geometry()
        geometry.setWidth(rect.width())
        geometry.setHeight(rect.height())
        geometry.moveCenter(rect.center())
        geometry.adjust(4, 4, -2, -2)
        self._line_edit.setGeometry(geometry)
        self._line_edit.setText(text)
        self._line_edit.setHidden(False)
        self._line_edit.setFocus()
        self._line_edit.selectAll()

    def _start_editing_tab(self, index: int):
        """Enter edit table name mode."""
        rect = self._tab_rect(index)
        self._current_edit_index = index
        self._move_line_edit(rect, self.tabText(index))
        return None

    if TYPE_CHECKING:

        def widget(self, index: int) -> QSubWindowArea | None: ...
        def currentWidget(self) -> QSubWindowArea | None: ...


class QRenameLineEdit(QtW.QLineEdit):
    def __init__(self, parent: QtW.QWidget):
        super().__init__(parent)
        self.setHidden(True)

    def keyPressEvent(self, a0: QtGui.QKeyEvent) -> None:
        if a0.key() == QtCore.Qt.Key.Key_Escape:
            self.setHidden(True)
        return super().keyPressEvent(a0)

    # def focusOutEvent(self, event: QtGui.QFocusEvent) -> None:
    #     self.setHidden(True)
    #     super().focusOutEvent(event)
