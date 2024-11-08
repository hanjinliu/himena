from __future__ import annotations

from qtpy import QtWidgets as QtW, QtCore
from royalapp.qt._qtitlebar import QTitleBar
from royalapp.types import (
    DockArea,
    DockAreaString,
)


class QDockWidget(QtW.QDockWidget):
    closed = QtCore.Signal()

    def __init__(
        self,
        widget: QtW.QWidget,
        title: str,
        allowed_areas: list[DockAreaString | DockArea] | None = None,
    ):
        super().__init__(title)
        # self.setAllowedAreas()
        self.setWidget(widget)
        _titlebar = QTitleBar(title, self)
        self.setTitleBarWidget(_titlebar)
        _titlebar.closeSignal.connect(self.close)
        if allowed_areas is None:
            allowed_areas = [
                DockArea.LEFT,
                DockArea.RIGHT,
                DockArea.TOP,
                DockArea.BOTTOM,
            ]
        else:
            allowed_areas = [DockArea(area) for area in allowed_areas]
        areas = QtCore.Qt.DockWidgetArea.NoDockWidgetArea
        for allowed_area in allowed_areas:
            areas |= _DOCK_AREA_MAP[allowed_area]
        return self.setAllowedAreas(areas)

    @staticmethod
    def area_normed(area) -> QtCore.Qt.DockWidgetArea:
        if area is not None:
            area = DockArea(area)
        return _DOCK_AREA_MAP[area]

    def closeEvent(self, event):
        self.closed.emit()
        super().closeEvent(event)


_DOCK_AREA_MAP = {
    DockArea.TOP: QtCore.Qt.DockWidgetArea.TopDockWidgetArea,
    DockArea.BOTTOM: QtCore.Qt.DockWidgetArea.BottomDockWidgetArea,
    DockArea.LEFT: QtCore.Qt.DockWidgetArea.LeftDockWidgetArea,
    DockArea.RIGHT: QtCore.Qt.DockWidgetArea.RightDockWidgetArea,
    None: QtCore.Qt.DockWidgetArea.NoDockWidgetArea,
}
