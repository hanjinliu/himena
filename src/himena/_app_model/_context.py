from typing import TYPE_CHECKING
from app_model.expressions import ContextKey, ContextNamespace
from himena.types import WindowState

if TYPE_CHECKING:
    from himena.widgets import MainWindow


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


def _num_sub_windows(ui: "MainWindow") -> int:
    if area := ui.tabs.current():
        return area.len()
    return 0


def _num_tabs(ui: "MainWindow") -> int:
    return ui.tabs.len()


def _active_window_model_type(ui: "MainWindow") -> str | None:
    if (area := ui.tabs.current()) and (win := area.current()) and win.is_exportable:
        out = win.model_type()
        if out is None:
            out = win.to_model().type
            if out is None:
                return None
        return out.split(".")[0]
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
    num_tabs = ContextKey(
        0,
        "number of tabs",
        _num_tabs,
    )
    num_sub_windows = ContextKey(
        0,
        "number of sub-windows in the current tab",
        _num_sub_windows,
    )
    active_window_model_type = ContextKey(
        None,
        "hash of the type of the model of the active window",
        _active_window_model_type,
    )

    def _update(self, ui):
        for k, v in self._getters.items():
            setattr(self, k, v(ui))
