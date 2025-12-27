from __future__ import annotations

import inspect
from pathlib import Path
from typing import (
    Callable,
    Generic,
    Hashable,
    Literal,
    TypeVar,
    TYPE_CHECKING,
    overload,
)

from himena.types import (
    WindowState,
    ClipboardDataModel,
    DockArea,
    DockAreaString,
    WindowRect,
    BackendInstructions,
    WidgetClassTuple,
)

if TYPE_CHECKING:
    import numpy as np
    from numpy.typing import NDArray
    from concurrent.futures import Future
    from himena.app import EventLoopHandler
    from himena.style import Theme
    from himena.widgets._main_window import MainWindow
    from himena.widgets._wrapper import SubWindow, ParametricWindow

_W = TypeVar("_W")  # backend widget type
_T = TypeVar("_T")


class BackendMainWindow(Generic[_W]):  # pragma: no cover
    _himena_main_window: MainWindow[_W]
    _event_loop_handler: EventLoopHandler

    def __init_subclass__(cls) -> None:
        for name in dir(BackendMainWindow):
            if not hasattr(cls, name):
                raise NotImplementedError(f"Method {name} is not implemented.")

    def _update_widget_theme(self, theme: Theme):
        """Update the theme of the main window."""

    def _main_window_rect(self) -> WindowRect:
        """Get the rect of the main window."""

    def _set_main_window_rect(self, rect: WindowRect) -> None:
        """Set the rect of the main window."""

    def _current_tab_index(self) -> int | None:
        """Get the current tab index.

        If there is no tab, return None.
        """

    def _set_current_tab_index(self, i_tab: int) -> None:
        """Update the current tab index."""

    def _tab_hash(self, i_tab: int) -> Hashable:
        """Get a hashable value of the tab at the index."""

    def _tab_hash_for_window(self, widget: _W) -> Hashable:
        """Get a hashable value of the tab containing the window."""

    def _num_tabs(self) -> int:
        """Get the number of tabs."""

    def _current_sub_window_index(self, i_tab: int) -> int | None:
        """Get the current sub window index in the given tab.

        If there is no sub window, or the tab area itself is selected, return None.
        """

    def _set_current_sub_window_index(self, i_tab: int, i_window: int | None) -> None:
        """Update the current sub window index in the given tab.

        if `i_window` is None, the tab area itself will be selected (all the windows
        will be deselected). `i_window` is asserted to be non-negative.
        """

    def _set_control_widget(self, widget: _W, control: _W | None) -> None:
        """Set the control widget for the given sub window widget.

        A control widget appears on the top-right corner of the toolbar, which will be
        used to display the state of the widget, edit the widget efficiently, etc. For
        example, a font size spinbox for a text editor widget.
        """

    def _update_control_widget(self, current: _W | None) -> None:
        """Switch the control widget to another one in the existing ones.

        If None is given, the control widget will be just hidden.
        """

    def _remove_control_widget(self, widget: _W) -> None:
        """Remove the control widget for the given sub window widget from the stack."""

    def _window_state(self, widget: _W) -> WindowState:
        """The state (min, normal, etc.) of the window."""

    def _set_window_state(
        self,
        widget: _W,
        state: WindowState,
        inst: BackendInstructions,
    ) -> None:
        """Update the state of the window.

        The BackendInstructions indicates the animation or other effects to be applied.
        """

    def _tab_title(self, i_tab: int) -> str:
        """Get the title of the tab at the index."""

    def _set_tab_title(self, i_tab: int, title: str) -> None:
        """Update the title of the tab at the index."""

    def _window_title(self, widget: _W) -> str:
        """Get the title of the window."""

    def _set_window_title(self, widget: _W, title: str) -> None:
        """Update the title of the window."""

    def _window_rect(self, widget: _W) -> WindowRect:
        """Get the rectangle relative to the tab area of the window."""

    def _set_window_rect(
        self,
        widget: _W,
        rect: WindowRect,
        inst: BackendInstructions,
    ) -> None:
        """Update the rectangle of the window.

        The BackendInstructions indicates the animation or other effects to be applied.
        """

    def _area_size(self) -> tuple[int, int]:
        """Get the size of the tab area."""

    @overload
    def _open_file_dialog(
        self,
        mode: Literal["r", "d", "w"] = "r",
        extension_default: str | None = None,
        allowed_extensions: list[str] | None = None,
        caption: str | None = None,
        start_path: Path | None = None,
    ) -> Path | None: ...
    @overload
    def _open_file_dialog(
        self,
        mode: Literal["rm"],
        extension_default: str | None = None,
        allowed_extensions: list[str] | None = None,
        caption: str | None = None,
        start_path: Path | None = None,
    ) -> list[Path] | None: ...

    def _open_file_dialog(
        self,
        mode,
        extension_default=None,
        allowed_extensions=None,
        caption=None,
        start_path=None,
    ):
        """Open a file dialog."""

    def _request_choice_dialog(
        self,
        title: str,
        message: str,
        choices: list[tuple[str, _T]],
        how: Literal["buttons", "radiobuttons"] = "buttons",
    ) -> _T | None:
        """Request a choice dialog and return the clicked text."""

    def _show_command_palette(self, kind: str) -> None:
        """Show the command palette widget of the given kind."""

    def _exit_main_window(self, confirm: bool = False) -> None:
        """Close the main window (confirm if needed)."""

    def _get_widget_list(self, i_tab: int) -> list[tuple[str, _W]]:
        """Get the list of widgets in the tab."""

    def _del_widget_at(self, i_tab: int, i_window: int) -> None:
        """Delete the `i_window`-th window in the `i_tab`-th tab."""

    def _del_tab_at(self, i_tab: int) -> None:
        """Delete the `i_tab`-th tab.

        Backend does not need to close the subwindows one by one (will be done on the
        wrapper side).
        """

    def _rename_window_at(self, i_tab: int, i_window: int) -> None:
        """Start renaming the `i_window`-th window in the `i_tab`-th tab."""

    def add_widget(self, widget: _W, i_tab: int, title: str) -> _W:
        """Add a sub window containing the widget to the tab at the index.

        Return the backend widget.
        """

    def set_widget_as_preview(self, widget: _W):
        """Set the widget state as the preview mode."""

    def add_tab(self, title: str) -> None:
        """Add a empty tab with the title."""

    def _mark_tab_as_single_window_mode(self, i_tab: int) -> None:
        """Mark the tab as single-window mode"""

    def add_dock_widget(
        self,
        widget: _W,
        title: str | None,
        area: DockAreaString | DockArea | None = DockArea.RIGHT,
        allowed_areas: list[DockAreaString | DockArea] | None = None,
    ) -> _W:
        """Add a dock widget containing the widget to the main window.

        Return the backend dock widget.
        """

    ### dock widgets ###
    def _dock_widget_visible(self, widget: _W) -> bool:
        """Whether the dock widget is visible."""

    def _set_dock_widget_visible(self, widget: _W, visible: bool) -> None:
        """Update the visibility of the dock widget."""

    def _dock_widget_title(self, widget: _W) -> str:
        """Get the title of the dock widget."""

    def _set_dock_widget_title(self, widget: _W, title: str) -> None:
        """Update the title of the dock widget."""

    def _del_dock_widget(self, widget: _W) -> None:
        """Delete the dock widget."""

    ### others ###
    def show(self, run: bool = False) -> None:
        """Show the main window and run the app immediately if `run` is True"""

    def _list_widget_class(
        self,
        type: str,
    ) -> tuple[list[WidgetClassTuple], type[_W]]:
        """List the available widget classes of the given type.

        The method will return (list of (widget model type, widget_class, priority),
        fallback class)
        """

    def _connect_main_window_signals(self, main_window: MainWindow[_W]):
        """Connect the signal of the backend main window to the callbacks."""

    def _connect_window_events(
        self,
        wrapper: SubWindow[_W],
        backend: _W,
    ):
        """Connect the events between the wrapper sub window and the backend widget."""

    def _update_context(self) -> None:
        """Update the application context."""

    def _clipboard_data(self) -> ClipboardDataModel | None:
        """Get the clipboard data."""

    def _set_clipboard_data(self, data: ClipboardDataModel) -> None:
        """Set the clipboard data."""

    def _screenshot(self, target: str) -> NDArray[np.uint8]:
        """Take a screenshot of the target area."""

    def _process_parametric_widget(self, widget: _W) -> _W:
        """Process a parametric widget so that it can be added to the main window.

        The incoming widget must implements the `get_params` method, which gives the
        dictionary of parameters.
        """

    def _connect_parametric_widget_events(
        self,
        wrapper: ParametricWindow[_W],
        widget: _W,
    ) -> None:
        """Connect the events between the wrapper parametric window and the backend."""

    def _signature_to_widget(
        self,
        sig: inspect.Signature,
        show_parameter_labels: bool = True,
        preview: bool = False,
    ) -> _W:
        """Convert a function signature to a widget that can run it."""

    def _add_widget_to_dialog(
        self,
        widget: _W,
        title: str,
    ) -> bool:
        """Convert a parametric widget to a dialog widget, and return the response."""

    def _add_widget_to_parametric_window(
        self,
        wrapper: ParametricWindow[_W],
        widget: _W,
        result_as: Literal["below", "right"],
    ) -> None:
        """Add a widget to the parametric window."""

    def _remove_widget_from_parametric_window(
        self,
        wrapper: ParametricWindow[_W],
    ) -> None:
        """Remove a widget from the parametric window."""

    def _move_focus_to(self, widget: _W) -> None:
        """Move the focus to the widget."""

    def _set_status_tip(self, tip: str, duration: float, behavior: str) -> None:
        """Set the status tip of the main window for a duration (sec)."""

    def _show_notification(self, text: str, duration: float) -> None:
        """Show notification for a duration (sec)."""

    def _show_tooltip(self, text: str, duration: float) -> None:
        """Show tooltip next to the cursor for a duration (sec)."""

    def _rebuild_for_runtime(self, new_menus: list[str]) -> None:
        """Register the actions at runtime."""

    def _process_future_done_callback(
        self,
        cb: Callable[[Future], None],
        cb_errored: Callable[[Exception], None],
        **kwargs,
    ) -> Callable[[Future], None]:
        """Wrap the callback of the future done event so that it can be run in the main
        thread."""

    def _set_parametric_widget_busy(self, wrapper: ParametricWindow[_W], busy: bool):
        """Set the parametric widget busy status (disable call button etc)."""

    def _add_job_progress(self, future: Future, desc: str, total: int = 0) -> None:
        """Add a job to the job stack."""

    def _add_whats_this(self, text: str, style: Literal["plain", "markdown", "html"]):
        """Add a what's this text to the main window."""

    def _append_result(self, item: dict[str, object]) -> None:
        """Append a new result to the result stack."""

    def _keys_as_set(self) -> set[int]:
        """Return the set of currently pressed key codes."""
