from __future__ import annotations


from royalapp.widgets import MainWindow
from qtpy import QtWidgets as QtW
from royalapp.qt._qmain_window import QMainWindow


class MainWindowQt(MainWindow[QtW.QWidget]):
    def __init__(self, app: str = "royalapp") -> None:
        backend = QMainWindow(app=app)
        super().__init__(backend, app)
        backend._royalapp_main_window = self
