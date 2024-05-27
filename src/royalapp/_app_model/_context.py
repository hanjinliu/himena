from app_model.expressions import ContextKey, ContextNamespace
from royalapp.widgets import MainWindow
from royalapp.types import SubWindowState


def _is_active_window_savable(ui: MainWindow) -> bool:
    widget = ui.tabs.current().current().is_
    return hasattr(widget, "export_data")


def _active_window_state(ui: MainWindow):
    widget = ui.tabs.current().current()
    return ui._backend_main_window._window_state(widget)


def _is_active_tab_empty(ui: MainWindow) -> bool:
    return ui.tabs.current().len() == 0


class MainWindowContexts(ContextNamespace[MainWindow]):
    is_active_window_savable = ContextKey(
        False,
        "if the current window is savable",
        _is_active_window_savable,
    )
    active_window_state = ContextKey(
        SubWindowState.NORMAL,
        "state of the sub-window",
        _active_window_state,
    )
    is_active_tab_empty = ContextKey(
        False,
        "if the current tab is empty",
        _is_active_tab_empty,
    )
