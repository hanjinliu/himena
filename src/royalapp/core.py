from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from royalapp.widgets import MainWindow
    from qtpy import QtWidgets as QtW


def new_window(app: str = "royalapp") -> MainWindow[QtW.QWidget]:
    from royalapp.qt import MainWindowQt

    return MainWindowQt(app)
