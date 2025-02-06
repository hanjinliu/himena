from himena.widgets._main_window import MainWindow, BackendMainWindow
from himena.widgets._widget_list import TabArea
from himena.widgets._wrapper import SubWindow, ParametricWindow, DockWidget
from himena.widgets._initialize import (
    current_instance,
    set_current_instance,
    remove_instance,
    init_application,
)
from himena.widgets._functions import set_status_tip, set_clipboard, notify

__all__ = [
    # widgets
    "MainWindow",
    "TabArea",
    "BackendMainWindow",
    "SubWindow",
    "ParametricWindow",
    "DockWidget",
    # functions
    "current_instance",
    "set_current_instance",
    "remove_instance",
    "init_application",
    "set_status_tip",
    "set_clipboard",
    "notify",
]
