from __future__ import annotations

from typing import TYPE_CHECKING, Iterator
from qtpy import QtWidgets as QtW
from royalapp.qt._qsub_window import QSubWindowArea


class QTabWidget(QtW.QTabWidget):
    def __init__(self):
        super().__init__()
        self.setTabBarAutoHide(True)
        self.tabBar().setMovable(True)
        self.currentChanged.connect(self._on_current_changed)

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
        return widget

    def iter_widgets(self) -> Iterator[QtW.QWidget]:
        """Iterate over all widgets in the tab widget."""
        for idx in self.count():
            area = self.widget(idx)
            yield from area.iter_widgets()

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
        self.widget(index)._reanchor_windows()

    if TYPE_CHECKING:

        def widget(self, index: int) -> QSubWindowArea: ...
        def currentWidget(self) -> QSubWindowArea | None: ...
