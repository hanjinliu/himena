from __future__ import annotations

from pathlib import Path
from typing import Generic, TypeVar, TYPE_CHECKING

import psygnal
from royalapp.types import (
    WidgetDataModel,
    SubWindowState,
    ClipBoardDataModel,
    DockArea,
    DockAreaString,
)

if TYPE_CHECKING:
    from royalapp.widgets._tab_list import SubWindow

_W = TypeVar("_W")  # backend widget type


class BackendMainWindow(Generic[_W]):
    def _current_tab_index(self) -> int | None:
        raise NotImplementedError

    def _set_current_tab_index(self, i_tab: int) -> None:
        raise NotImplementedError

    def _current_sub_window_index(self) -> int | None:
        raise NotImplementedError

    def _set_current_sub_window_index(self, i_window: int) -> None:
        raise NotImplementedError

    def _window_state(self, widget: _W) -> SubWindowState:
        raise NotImplementedError

    def _set_window_state(self, widget: _W, state: SubWindowState) -> None:
        raise NotImplementedError

    def _set_tab_title(self, i_tab: int, title: str) -> None:
        raise NotImplementedError

    def _window_title(self, widget: _W) -> str:
        raise NotImplementedError

    def _set_window_title(self, widget: _W, title: str) -> None:
        raise NotImplementedError

    def _provide_file_output(self) -> WidgetDataModel:
        raise NotImplementedError

    def _open_file_dialog(self, mode: str = "r") -> Path | list[Path] | None:
        raise NotImplementedError

    def _open_confirmation_dialog(self, message: str) -> bool:
        raise NotImplementedError

    def _exit_main_window(self) -> None:
        raise NotImplementedError

    def _get_widget_list(self, i_tab: int) -> list[tuple[str, _W]]:
        raise NotImplementedError

    def _del_widget_at(self, i_tab: int, i_window: int) -> None:
        raise NotImplementedError

    def _get_tab_name_list(self) -> list[str]:
        raise NotImplementedError

    def _del_tab_at(self, i_tab: int) -> None:
        raise NotImplementedError

    def add_widget(self, widget: _W, i_tab: int, title: str) -> _W:
        raise NotImplementedError

    def add_tab(self, title: str) -> None:
        raise NotImplementedError

    def add_dock_widget(
        self,
        widget: _W,
        title: str | None,
        area: DockAreaString | DockArea | None = DockArea.RIGHT,
        allowed_areas: list[DockAreaString | DockArea] | None = None,
    ) -> _W:
        raise NotImplementedError

    def show(self, run: bool = False) -> None:
        raise NotImplementedError

    def _run_app(self):
        raise NotImplementedError

    def _pick_widget_class(self, type: str) -> type[_W]:
        raise NotImplementedError

    def _connect_activation_signal(self, sig: psygnal.SignalInstance):
        raise NotImplementedError

    def _connect_window_events(self, sub: SubWindow, backend: _W):
        raise NotImplementedError

    def _update_context(self) -> None:
        raise NotImplementedError

    def _clipboard_data(self) -> ClipBoardDataModel | None:
        raise NotImplementedError
