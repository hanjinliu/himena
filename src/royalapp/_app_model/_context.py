from typing import TYPE_CHECKING
from app_model.expressions import ContextKey, ContextNamespace
from royalapp.types import SubWindowState

if TYPE_CHECKING:
    from royalapp.widgets import MainWindow


def _is_active_window_savable(ui: "MainWindow") -> bool:
    if area := ui.tabs.current_or():
        if win := area.current_or():
            return win.is_exportable
    return False


def _active_window_state(ui: "MainWindow"):
    if area := ui.tabs.current_or():
        if win := area.current_or():
            return win.state
    return SubWindowState.NORMAL


def _is_active_tab_empty(ui: "MainWindow") -> bool:
    if area := ui.tabs.current_or():
        return area.len() == 0
    return True


def _active_window_model_type(ui: "MainWindow") -> str | None:
    if area := ui.tabs.current_or():
        if win := area.current_or():
            if win.is_exportable:
                return win.to_model().type
    return None


class AppContext(ContextNamespace["MainWindow"]):
    is_active_window_exportable = ContextKey(
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
    active_window_model_type = ContextKey(
        None,
        "type of the model of the active window",
        _active_window_model_type,
    )

    def _update(self, ui):
        for k, v in self._getters.items():
            setattr(self, k, v(ui))
