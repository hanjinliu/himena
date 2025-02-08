from __future__ import annotations

from typing import TYPE_CHECKING
from himena.widgets import MainWindow
from himena.qt._qmain_window import QMainWindow

if TYPE_CHECKING:
    from app_model import Application
    from himena.style import Theme


class MainWindowQt(MainWindow["QtW.QWidget"]):
    """Main window with Qt backend."""

    _backend_main_window: QMainWindow

    def __init__(self, app: Application, theme: Theme) -> None:
        backend = QMainWindow(app=app)
        super().__init__(backend, app, theme)
        backend._himena_main_window = self
        backend._tab_widget._init_startup()
        backend._update_context()
