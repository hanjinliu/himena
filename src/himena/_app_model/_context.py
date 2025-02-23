from typing import TYPE_CHECKING
from app_model.expressions import ContextKey, ContextNamespace
from himena.types import WindowState
from himena._utils import get_widget_class_id, get_user_context

if TYPE_CHECKING:
    from himena.widgets import MainWindow


def _is_active_window_savable(ui: "MainWindow") -> bool:
    if win := ui.current_window:
        return win.supports_to_model
    return False


def _is_active_window_editable(ui: "MainWindow") -> bool:
    if win := ui.current_window:
        return win.is_editable
    return False


def _active_window_state(ui: "MainWindow"):
    if win := ui.current_window:
        return win.state
    return WindowState.NORMAL


def _is_active_window_focused(ui: "MainWindow") -> bool:
    return ui.current_window is not None


def _num_sub_windows(ui: "MainWindow") -> int:
    if area := ui.tabs.current():
        return area.len()
    return 0


def _num_tabs(ui: "MainWindow") -> int:
    return ui.tabs.len()


def _get_model_types(ui: "MainWindow") -> str | None:
    try:
        if (win := ui.current_window) and win.supports_to_model:
            out = win.model_type()
            if out is None:
                out = win.to_model().type
                if out is None:
                    return None
            return out.split(".")
    except Exception:
        return None
    return None


def _active_window_model_type(ui: "MainWindow") -> str | None:
    if out := _get_model_types(ui):
        return out[0]
    return None


def _active_window_model_subtype_1(ui: "MainWindow") -> str | None:
    if out := _get_model_types(ui):
        if len(out) < 2:
            return None
        return out[1]
    return None


def _active_window_model_subtype_2(ui: "MainWindow") -> str | None:
    if out := _get_model_types(ui):
        if len(out) < 3:
            return None
        return out[2]
    return None


def _active_window_model_subtype_3(ui: "MainWindow") -> str | None:
    if out := _get_model_types(ui):
        if len(out) < 4:
            return None
        return out[3]
    return None


def _active_window_widget_id(ui: "MainWindow") -> str | None:
    if win := ui.current_window:
        return get_widget_class_id(type(win.widget))
    return None


def _get_user_context(ui: "MainWindow") -> dict | None:
    if area := ui.tabs.current():
        if win := area.current():
            return get_user_context(win.widget)
    return None


class AppContext(ContextNamespace["MainWindow"]):
    """Context namespace for the himena main window."""

    is_active_window_supports_to_model = ContextKey(
        False,
        "if the current window supports to_model method",
        _is_active_window_savable,
    )
    is_active_window_editable = ContextKey(
        False,
        "if the current window is editable",
        _is_active_window_editable,
    )
    active_window_state = ContextKey(
        WindowState.NORMAL,
        "state of the sub-window",
        _active_window_state,
    )
    is_subwindow_focused = ContextKey(
        False,
        "if a sub-window is focused",
        _is_active_window_focused,
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
        "type of the model of the active window",
        _active_window_model_type,
    )
    active_window_model_subtype_1 = ContextKey(
        None,
        "subtype of the model of the active window",
        _active_window_model_subtype_1,
    )
    active_window_model_subtype_2 = ContextKey(
        None,
        "subtype of the model of the active window",
        _active_window_model_subtype_2,
    )
    active_window_model_subtype_3 = ContextKey(
        None,
        "subtype of the model of the active window",
        _active_window_model_subtype_3,
    )
    active_window_widget_id = ContextKey(
        None,
        "widget class id of the active window",
        _active_window_widget_id,
    )
    user_context = ContextKey(
        None,
        "User-defined context",
        _get_user_context,
    )

    def _update(self, ui):
        for k, v in self._getters.items():
            setattr(self, k, v(ui))
