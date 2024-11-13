from __future__ import annotations

import inspect
from pathlib import Path
from typing import Callable, Generic, Literal, TypeVar, TYPE_CHECKING, overload

from himena.anchor import WindowAnchor
from himena.types import (
    WindowState,
    ClipboardDataModel,
    DockArea,
    DockAreaString,
    WindowRect,
    BackendInstructions,
)

if TYPE_CHECKING:
    from himena.style import Theme
    from himena.widgets._main_window import MainWindow
    from himena.widgets._wrapper import SubWindow, DockWidget, ParametricWindow
    import numpy as np
    from numpy.typing import NDArray

_W = TypeVar("_W")  # backend widget type


class BackendMainWindow(Generic[_W]):  # pragma: no cover
    _himena_main_window: MainWindow

    def _update_widget_theme(self, theme: Theme):
        raise NotImplementedError

    def _current_tab_index(self) -> int | None:
        raise NotImplementedError

    def _set_current_tab_index(self, i_tab: int) -> None:
        raise NotImplementedError

    def _current_sub_window_index(self) -> int | None:
        raise NotImplementedError

    def _set_current_sub_window_index(self, i_window: int) -> None:
        raise NotImplementedError

    def _window_state(self, widget: _W) -> WindowState:
        raise NotImplementedError

    def _set_window_state(
        self,
        widget: _W,
        state: WindowState,
        inst: BackendInstructions,
    ) -> None:
        raise NotImplementedError

    def _tab_title(self, i_tab: int) -> str:
        raise NotImplementedError

    def _set_tab_title(self, i_tab: int, title: str) -> None:
        raise NotImplementedError

    def _window_title(self, widget: _W) -> str:
        raise NotImplementedError

    def _set_window_title(self, widget: _W, title: str) -> None:
        raise NotImplementedError

    def _window_rect(self, widget: _W) -> WindowRect:
        raise NotImplementedError

    def _set_window_rect(
        self,
        widget: _W,
        rect: WindowRect,
        inst: BackendInstructions,
    ) -> None:
        raise NotImplementedError

    def _window_anchor(self, widget: _W) -> WindowAnchor:
        raise NotImplementedError

    def _set_window_anchor(self, widget: _W, anchor: WindowAnchor) -> None:
        raise NotImplementedError

    def _area_size(self) -> tuple[int, int]:
        raise NotImplementedError

    @overload
    def _open_file_dialog(
        self,
        mode: Literal["r", "d", "w"] = "r",
        extension_default: str | None = None,
        allowed_extensions: list[str] | None = None,
    ) -> Path | None: ...
    @overload
    def _open_file_dialog(
        self,
        mode: Literal["rm"],
        extension_default: str | None = None,
        allowed_extensions: list[str] | None = None,
    ) -> list[Path] | None: ...

    def _open_file_dialog(self, mode, extension_default=None, allowed_extensions=None):
        raise NotImplementedError

    def _open_confirmation_dialog(self, message: str) -> bool:
        raise NotImplementedError

    def _open_selection_dialog(self, msg: str, options: list[str]) -> list[str] | None:
        raise NotImplementedError

    def _request_values(
        self, msg: str, spec: dict[str, type]
    ) -> dict[str, object] | None:
        raise NotImplementedError

    def _show_command_palette(self, kind: str) -> None:
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
        # NOTE: backend does not need to close the subwindows one by one
        raise NotImplementedError

    def _rename_window_at(self, i_tab: int, i_window: int) -> None:
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
        keybindings=None,
    ) -> DockWidget[_W]:
        raise NotImplementedError

    def add_dialog_widget(self, widget: _W, title: str | None):
        raise NotImplementedError

    ### dock widgets ###
    def _dock_widget_visible(self, widget: _W) -> bool:
        raise NotImplementedError

    def _set_dock_widget_visible(self, widget: _W, visible: bool) -> None:
        raise NotImplementedError

    def _dock_widget_title(self, widget: _W) -> str:
        raise NotImplementedError

    def _set_dock_widget_title(self, widget: _W, title: str) -> None:
        raise NotImplementedError

    def _del_dock_widget(self, widget: _W) -> None:
        raise NotImplementedError

    ### others ###
    def show(self, run: bool = False) -> None:
        raise NotImplementedError

    def _run_app(self):
        raise NotImplementedError

    def _list_widget_class(
        self,
        type: str,
    ) -> tuple[list[tuple[str, type[_W], int]], type[_W]]:
        # (list of available classes, fallback class)
        raise NotImplementedError

    def _connect_activation_signal(
        self,
        cb_tab: Callable[[int], int],
        cb_win: Callable[[], SubWindow[_W]],
    ):
        raise NotImplementedError

    def _connect_window_events(
        self,
        wrapper: SubWindow[_W],
        backend: _W,
    ):
        raise NotImplementedError

    def _update_context(self) -> None:
        raise NotImplementedError

    def _clipboard_data(self) -> ClipboardDataModel | None:
        raise NotImplementedError

    def _set_clipboard_data(self, data: ClipboardDataModel) -> None:
        raise NotImplementedError

    def _screenshot(self, target: str) -> NDArray[np.uint8]:
        raise NotImplementedError

    def _process_parametric_widget(self, widget: _W) -> _W:
        # widget implements "get_params". This method will return a new widget that
        # can be directly passed to ui.add_widget().
        raise NotImplementedError

    def _connect_parametric_widget_events(
        self,
        wrapper: ParametricWindow[_W],
        widget: _W,
    ) -> None:
        raise NotImplementedError

    def _signature_to_widget(
        self,
        sig: inspect.Signature,
        preview: bool = False,
    ) -> _W:
        raise NotImplementedError

    def _move_focus_to(self, widget: _W) -> None:
        raise NotImplementedError
