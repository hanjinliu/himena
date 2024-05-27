from __future__ import annotations

from pathlib import Path
from typing import Generic, TypeVar
from royalapp.types import TabTitle, WindowTitle, WidgetDataModel, SubWindowState

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

    def _set_tab_title(self, i_tab: int, title: TabTitle) -> None:
        raise NotImplementedError

    def _window_title(self, widget: _W) -> WindowTitle:
        raise NotImplementedError

    def _set_window_title(self, widget: _W, title: WindowTitle) -> None:
        raise NotImplementedError

    def _pick_widget_class(self, file_data: WidgetDataModel) -> type[_W]:
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

    def add_widget(self, widget: _W, i_tab: int, title: str) -> None:
        raise NotImplementedError

    def add_tab(self, title: TabTitle) -> None:
        raise NotImplementedError

    def add_dock_widget(self, widget: _W) -> None:
        raise NotImplementedError

    def show(self, run: bool = False) -> None:
        raise NotImplementedError

    def _run_app(self):
        raise NotImplementedError

    def _pick_widget_class(self, type: str) -> _W:
        raise NotImplementedError
