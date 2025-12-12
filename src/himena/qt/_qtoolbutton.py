from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from qtpy import QtWidgets as QtW
from himena.qt._qsvg import QColoredSVGIcon

if TYPE_CHECKING:
    from himena.style import Theme


class QColoredToolButton(QtW.QToolButton):
    """Tool button that is aware of the application theme."""

    def __init__(self, callback, svg_path):
        super().__init__()
        self._icon_path = Path(svg_path)
        self.setToolTip(callback.__doc__ or "")
        self.clicked.connect(callback)
        self._callback = callback

    def update_theme(self, theme: Theme):
        """Update the theme of the control."""
        color = theme.foreground
        self.setIcon(QColoredSVGIcon.fromfile(self._icon_path, color))
