from __future__ import annotations

from app_model import Application
from qtpy import QtWidgets as QtW
from himena.style import Theme
from himena.widgets import MainWindow
from himena.qt._qmain_window import QMainWindow


class MainWindowQt(MainWindow[QtW.QWidget]):
    """Main window with Qt backend."""

    _backend_main_window: QMainWindow

    def __init__(self, app: Application, theme: Theme) -> None:
        backend = QMainWindow(app=app)
        super().__init__(backend, app, theme)
        backend._himena_main_window = self
        backend._tab_widget._init_startup()
