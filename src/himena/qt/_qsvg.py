from __future__ import annotations

from pathlib import Path
from qtpy import QtGui, QtCore, QtSvg
from qtpy.QtCore import Qt

# These classes are mostly copied from napari/_qt/qt_resources/_svg.py
# See https://github.com/napari/napari/blob/main/napari/_qt/qt_resources/_svg.py


class SVGBufferIconEngine(QtGui.QIconEngine):
    def __init__(self, xml: str | bytes) -> None:
        if isinstance(xml, str):
            xml = xml.encode("utf-8")
        self.data = QtCore.QByteArray(xml)
        super().__init__()

    def paint(self, painter: QtGui.QPainter, rect, mode, state):
        """Paint the icon int ``rect`` using ``painter``."""
        renderer = QtSvg.QSvgRenderer(self.data)
        renderer.setAspectRatioMode(Qt.AspectRatioMode.KeepAspectRatio)
        renderer.render(painter, QtCore.QRectF(rect))

    def clone(self):
        """Required to subclass abstract QIconEngine."""
        return SVGBufferIconEngine(self.data)

    def pixmap(self, size, mode, state):
        """Return the icon as a pixmap with requested size, mode, and state."""
        img = QtGui.QImage(size, QtGui.QImage.Format.Format_ARGB32)
        img.fill(Qt.GlobalColor.transparent)
        pixmap = QtGui.QPixmap.fromImage(img, Qt.ImageConversionFlag.NoFormatConversion)
        painter = QtGui.QPainter(pixmap)
        self.paint(painter, QtCore.QRect(QtCore.QPoint(0, 0), size), mode, state)
        return pixmap


class QColoredSVGIcon(QtGui.QIcon):
    _COLOR_ARG = "currentColor"

    def __init__(
        self,
        xml: str,
        color: str = "#000000",
    ) -> None:
        self._color = QtGui.QColor(color)
        self._xml = xml
        colorized = xml.replace(self._COLOR_ARG, self._color.name())
        super().__init__(SVGBufferIconEngine(colorized))

    @classmethod
    def fromfile(cls: type[QColoredSVGIcon], path: str | Path, color="#000000"):
        with open(path) as f:
            xml = f.read()
        return cls(xml, color=color)
