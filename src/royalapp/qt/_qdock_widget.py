from __future__ import annotations

from qtpy import QtWidgets as QtW
from royalapp.qt._qtitlebar import QTitleBar


class QDockWidget(QtW.QDockWidget):
    def __init__(self, widget: QtW.QWidget, title: str):
        super().__init__(title)
        # self.setAllowedAreas()
        self.setWidget(widget)
        _titlebar = QTitleBar(title, self)
        self.setTitleBarWidget(_titlebar)
        _titlebar.closeSignal.connect(self.close)
