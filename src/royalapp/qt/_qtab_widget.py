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

    def addTabArea(self, tab_name: str) -> QSubWindowArea:
        """
        Add a new tab with a sub-window area.

        Parameters
        ----------
        tab_name : str
            Name of the tab.
        """
        widget = QSubWindowArea()
        self.addTab(widget, tab_name)
        return widget

    def iter_widgets(self) -> Iterator[QtW.QWidget]:
        """Iterate over all widgets in the tab widget."""
        for idx in self.count():
            area = self.widget(idx)
            yield from area.iter_widgets()
    
    def _on_current_changed(self, index: int) -> None:
        self.widget(index)._anchor_minimized_windows()

    if TYPE_CHECKING:
        def widget(self, index: int) -> QSubWindowArea: ...
        def currentWidget(self) -> QSubWindowArea | None: ...
