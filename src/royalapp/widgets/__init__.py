from royalapp.widgets._main_window import MainWindow, BackendMainWindow
from royalapp.widgets._wrapper import SubWindow, DockWidget
from royalapp.widgets._initialize import (
    current_instance,
    set_current_instance,
    remove_instance,
    init_application,
)

__all__ = [
    "MainWindow",
    "BackendMainWindow",
    "SubWindow",
    "DockWidget",
    "current_instance",
    "set_current_instance",
    "remove_instance",
    "init_application",
]
