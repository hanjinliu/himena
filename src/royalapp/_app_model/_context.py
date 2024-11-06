from typing import TYPE_CHECKING
from app_model.expressions import ContextKey, ContextNamespace
from royalapp.types import WindowState

if TYPE_CHECKING:
    from royalapp.widgets import MainWindow


def _is_active_window_savable(ui: "MainWindow") -> bool:
    if area := ui.tabs.current():
        if win := area.current():
            return win.is_exportable
    return False


def _active_window_state(ui: "MainWindow"):
    if area := ui.tabs.current():
        if win := area.current():
            return win.state
    return WindowState.NORMAL


def _has_sub_windows(ui: "MainWindow") -> bool:
    if area := ui.tabs.current():
        return area.len() > 0
    return False


def _has_tabs(ui: "MainWindow") -> bool:
    return ui.tabs.len() > 0


def _active_window_model_type(ui: "MainWindow") -> str | None:
    if (area := ui.tabs.current()) and (win := area.current()) and win.is_exportable:
        out = win.to_model().type
        if out is None:
            return None
        return out
    return None


class AppContext(ContextNamespace["MainWindow"]):
    is_active_window_exportable = ContextKey(
        False,
        "if the current window is savable",
        _is_active_window_savable,
    )
    active_window_state = ContextKey(
        WindowState.NORMAL,
        "state of the sub-window",
        _active_window_state,
    )
    has_tabs = ContextKey(
        False,
        "if the current window has tabs",
        _has_tabs,
    )
    has_sub_windows = ContextKey(
        False,
        "if the current tab is empty",
        _has_sub_windows,
    )
    active_window_model_type = ContextKey(
        None,
        "hash of the type of the model of the active window",
        _active_window_model_type,
    )

    def _update(self, ui):
        for k, v in self._getters.items():
            setattr(self, k, v(ui))
