from __future__ import annotations

from typing import TYPE_CHECKING
from qtpy import QtWidgets as QtW, QtCore, QtGui

if TYPE_CHECKING:
    from royalapp.qt.main_window import QMainWindow


class QWindowListWidget(QtW.QListWidget):
    def __init__(self):
        super().__init__()
        self.setSelectionBehavior(QtW.QAbstractItemView.SelectionBehavior.SelectRows)
        self.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)


def line_edit(text: str):
    line = QtW.QLineEdit()
    line.setText(text)
    line.setEnabled(False)
    font = line.font()
    font.setPointSize(12)
    font.setBold(True)
    line.setFont(font)
    line.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
    return line


BIG_INT = 999999


class QGotoWidget(QtW.QWidget):
    def __init__(self, main: QMainWindow):
        super().__init__(main)
        self._main = main
        self._list_widgets: list[QWindowListWidget] = []
        self._stack = QtW.QStackedWidget()
        layout = QtW.QVBoxLayout(self)
        layout.addWidget(self._stack)

    def update_ui(self):
        while self._stack.count() > 0:
            self._stack.removeWidget(self._stack.widget(0))
        self._list_widgets.clear()
        main = self._main._royalapp_main_window
        tab = main.tabs.current()
        if tab is None:
            raise ValueError("No tab is opened.")
        for i_tab, tab in enumerate(main.tabs):
            area = QtW.QWidget()
            layout = QtW.QVBoxLayout(area)
            layout.addWidget(line_edit(f"({i_tab}) {tab.name}"))
            list_widget = QWindowListWidget()
            for i_win, win in enumerate(tab):
                list_widget.addItem(win.title)
            layout.addWidget(list_widget)
            self._stack.addWidget(area)
            list_widget.itemClicked.connect(self.activate_window_for_item)
            self._list_widgets.append(list_widget)
        lw = self.currentListWidget()
        self._stack.setCurrentIndex(main.tabs.current_index)
        lw.setCurrentRow(main.tabs.current().current_index)
        lw.setFocus()

    def currentListWidget(self) -> QtW.QListWidget:
        return self._list_widgets[self._stack.currentIndex()]

    def show(self) -> None:
        cur = self._main._tab_widget.currentWidget()
        self.update_ui()
        center = self._main.mapFromGlobal(cur.mapToGlobal(cur.rect().center()))
        dx = 188
        dy = 270
        rect = QtCore.QRect(center.x() - dx // 2, center.y() - dy // 2, dx, dy)
        self.setGeometry(rect)
        super().show()
        self._force_list_item_selected()
        return None

    def keyPressEvent(self, a0: QtGui.QKeyEvent | None) -> None:
        if a0 is None:
            return
        nr = self.currentListWidget().count()
        nc = self._stack.count()
        _ctrl = a0.modifiers() & QtCore.Qt.KeyboardModifier.ControlModifier
        move = BIG_INT if _ctrl else 1
        if a0.key() == QtCore.Qt.Key.Key_Escape:
            self.close()
        elif a0.key() == QtCore.Qt.Key.Key_Return:
            self.activate_window_for_current_index()
        elif a0.key() == QtCore.Qt.Key.Key_Up:
            self.currentListWidget().setCurrentRow(
                max(self.currentListWidget().currentRow() - move, 0)
            )
            self._force_list_item_selected()
            self.setFocus()
        elif a0.key() == QtCore.Qt.Key.Key_Down:
            self.currentListWidget().setCurrentRow(
                min(self.currentListWidget().currentRow() + move, nr - 1)
            )
            self._force_list_item_selected()
            self.setFocus()
        elif a0.key() == QtCore.Qt.Key.Key_Left:
            self._stack.setCurrentIndex(max(self._stack.currentIndex() - move, 0))
            self._force_list_item_selected()
            self.setFocus()
        elif a0.key() == QtCore.Qt.Key.Key_Right:
            self._stack.setCurrentIndex(min(self._stack.currentIndex() + move, nc - 1))
            self._force_list_item_selected()
            self.setFocus()
        else:
            return super().keyPressEvent(a0)

    def _force_list_item_selected(self):
        lw = self.currentListWidget()
        lw.setCurrentRow(max(lw.currentRow(), 0))

    def activate_window_for_item(self, item: QtW.QListWidgetItem | None = None):
        if item is None:
            self.close()
            return
        return self.activate_window_for_current_index()

    def activate_window_for_current_index(self):
        i_tab = self._stack.currentIndex()
        i_win = self.currentListWidget().currentRow()
        main = self._main._royalapp_main_window
        main.tabs.current_index = i_tab
        main.tabs.current().current_index = i_win
        self.close()
        return None

    def focusOutEvent(self, a0: QtGui.QFocusEvent) -> None:
        self.close()
        return super().focusOutEvent(a0)
