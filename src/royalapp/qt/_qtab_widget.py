from __future__ import annotations

from typing import Iterator
from qtpy import QtWidgets as QtW
from qtpy import QtCore, QtGui
from royalapp.qt._qclickable_label import QClickableLabel
from royalapp.qt._qsub_window import QSubWindowArea
from royalapp.qt._qrename import QRenameLineEdit
from royalapp.qt._utils import get_main_window


class QTabWidget(QtW.QTabWidget):
    newWindowActivated = QtCore.Signal()

    def __init__(self):
        super().__init__()
        self._line_edit = QRenameLineEdit(self)
        self._current_edit_index = None

        @self._line_edit.rename_requested.connect
        def _(new_name: str):
            if self._current_edit_index is not None:
                new_name = self._coerce_tab_name(new_name)
                self.setTabText(self._current_edit_index, new_name)

        self.setTabBarAutoHide(False)
        self.tabBar().setMovable(False)
        self.currentChanged.connect(self._on_current_changed)
        self.tabBarDoubleClicked.connect(self._start_editing_tab)
        self.setSizePolicy(
            QtW.QSizePolicy.Policy.Expanding, QtW.QSizePolicy.Policy.Expanding
        )
        self.setMinimumSize(200, 200)
        self.setAcceptDrops(True)

        self.newWindowActivated.connect(self._repolish)

    def _init_startup(self):
        self._startup_widget = QStartupWidget(self)
        self._add_startup_widget()

    def add_tab_area(self, tab_name: str | None = None) -> QSubWindowArea:
        """
        Add a new tab with a sub-window area.

        Parameters
        ----------
        tab_name : str
            Name of the tab.
        """
        if tab_name is None:
            tab_name = "Tab"
        if self._is_startup_only():
            self.removeTab(0)
            self.setTabBarAutoHide(False)
        widget = QSubWindowArea()
        self.addTab(widget, self._coerce_tab_name(tab_name))
        widget.subWindowActivated.connect(self._emit_current_indices)
        return widget

    def remove_tab_area(self, index: int) -> None:
        if self._is_startup_only():
            raise ValueError("No tab in the tab widget.")
        self.removeTab(index)
        if self.count() == 0:
            self._add_startup_widget()
        return None

    def _add_startup_widget(self):
        self.addTab(self._startup_widget, ".welcome")
        self.setTabBarAutoHide(True)

    def _is_startup_only(self) -> bool:
        return self.count() == 1 and self.widget(0) == self._startup_widget

    def iter_widgets(self) -> Iterator[QtW.QWidget]:
        """Iterate over all widgets in the tab widget."""
        for idx in self.count():
            area = self.widget_area(idx)
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
        if widget := self.widget_area(index):
            widget._reanchor_windows()
            self._emit_current_indices()
            self._line_edit.setHidden(True)

    def _repolish(self) -> None:
        if area := self.current_widget_area():
            wins = area.subWindowList()
            cur = area.currentSubWindow()
            for i, win in enumerate(wins):
                win.set_is_current(win == cur)

    def _current_indices(self) -> tuple[int, int]:
        if widget := self.current_widget_area():
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

    def dragEnterEvent(self, e: QtGui.QDragEnterEvent) -> None:
        # This override is necessary for accepting drops from files.
        e.accept()

    def dropEvent(self, event: QtGui.QDropEvent) -> None:
        mime_data = event.mimeData()
        if mime_data.hasUrls():
            urls = mime_data.urls()
            for url in urls:
                if url.isLocalFile():
                    path = url.toLocalFile()
                    get_main_window(self).read_file(path)
        return super().dropEvent(event)

    def widget_area(self, index: int) -> QSubWindowArea | None:
        """Get the QSubWindowArea widget at index."""
        if self._is_startup_only():
            return None
        return self.widget(index)

    def current_widget_area(self) -> QSubWindowArea | None:
        """Get the current QSubWindowArea widget."""
        if self._is_startup_only():
            return None
        return self.currentWidget()


class QStartupWidget(QtW.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        _layout = QtW.QVBoxLayout(self)
        _layout.setContentsMargins(12, 12, 12, 12)
        _layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)

        self._open_file_btn = self.make_button("open-file", "Ctrl+O")
        self._open_folder_btn = self.make_button("open-folder", "Ctrl+K, Ctrl+O")
        self._open_recent_btn = self.make_button("open-recent", "Ctrl+K, Ctrl+R")

        _layout.addWidget(self._open_file_btn)
        _layout.addWidget(self._open_folder_btn)
        _layout.addWidget(self._open_recent_btn)
        self.setMinimumSize(0, 0)
        return None

    def make_button(self, command_id: str, shortcut: str) -> QClickableLabel:
        def callback():
            get_main_window(self).model_app.commands.execute_command(command_id)

        cmd = get_main_window(self).model_app.commands[command_id]

        label = QClickableLabel(f"{cmd.title} ({shortcut})")
        label.clicked.connect(callback)
        return label
