from __future__ import annotations

from qtpy import QtWidgets as QtW

class QDockWidget(QtW.QDockWidget):
    def __init__(self, widget: QtW.QWidget, title: str):
        super().__init__(title)
        # self.setAllowedAreas()
        self.setWidget(widget)
