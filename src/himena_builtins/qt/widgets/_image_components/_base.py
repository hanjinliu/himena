from __future__ import annotations

from typing import TypeVar
from qtpy import QtWidgets as QtW
from qtpy.QtCore import Qt

_I = TypeVar("_I", bound=QtW.QGraphicsItem)


class QBaseGraphicsScene(QtW.QGraphicsScene):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._grab_source: QtW.QGraphicsItem | None = None

    def grabSource(self) -> QtW.QGraphicsItem | None:
        return self._grab_source

    def setGrabSource(self, item: QtW.QGraphicsItem | None):
        self._grab_source = item


class QBaseGraphicsView(QtW.QGraphicsView):
    def __init__(self):
        scene = QBaseGraphicsScene()
        super().__init__(scene)
        self.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignHCenter)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setMouseTracking(True)
        self._scene = scene

    def addItem(self, item: _I) -> _I:
        self.scene().addItem(item)
        return item

    def scene(self) -> QBaseGraphicsScene:
        return self._scene
