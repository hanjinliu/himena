from __future__ import annotations

import inspect
from typing import TYPE_CHECKING, Any, Callable, Hashable, Literal, TypeVar
from himena.types import (
    BackendInstructions,
    ClipboardDataModel,
    DockArea,
    DockAreaString,
    WidgetClassTuple,
    WindowRect,
    WindowState,
)
from himena.widgets import MainWindow
from himena.style import Theme
from himena.widgets import BackendMainWindow
from himena.mock.widget import (
    MockWidget,
    MockSubWindow,
    MockTab,
    MockDockWidget,
    MockParametricWidget,
    MockModelWrapper,
)

if TYPE_CHECKING:
    from concurrent.futures import Future
    from app_model import Application
    from himena.style import Theme
    from himena.widgets._main_window import MainWindow
    from himena.widgets._wrapper import ParametricWindow

_T = TypeVar("_T")


class MainWindowMock(MainWindow["MockBackend"]):
    """A mock instance of main window."""

    _backend_main_window: MockBackend

    def __init__(self, app: Application, theme: Theme) -> None:
        backend = MockBackend()
        super().__init__(backend, app, theme)
        backend._himena_main_window = self
        backend._update_context()


class MockBackend(BackendMainWindow):
    def __init__(self):
        self._tabs: list[MockTab] = []
        self._dock_widgets: list[MockDockWidget] = []
        self._rect = WindowRect(0, 0, 800, 600)
        self._tab_index: int | None = None
        self.__area_size = (800, 600)

    def _update_widget_theme(self, theme: Theme):
        """Update the theme of the main window."""

    def _main_window_rect(self) -> WindowRect:
        """Get the rect of the main window."""
        return self._rect

    def _set_main_window_rect(self, rect: WindowRect) -> None:
        """Set the rect of the main window."""
        self._rect = rect

    def _current_tab_index(self) -> int | None:
        return self._tab_index

    def _set_current_tab_index(self, i_tab: int) -> None:
        """Update the current tab index."""
        self._tab_index = i_tab

    def _tab_hash(self, i_tab: int) -> Hashable:
        """Get a hashable value of the tab at the index."""
        return self._tabs[i_tab]

    def _tab_hash_for_window(self, widget: MockWidget) -> Hashable:
        """Get a hashable value of the tab containing the window."""
        return widget.subwindow.tab

    def _num_tabs(self) -> int:
        """Get the number of tabs."""
        return len(self._tabs)

    def _current_sub_window_index(self, i_tab: int) -> int | None:
        """Get the current sub window index in the given tab.

        If there is no sub window, or the tab area itself is selected, return None.
        """
        return self._tabs[i_tab].current_index

    def _set_current_sub_window_index(self, i_tab: int, i_window: int | None) -> None:
        """Update the current sub window index in the given tab.

        if `i_window` is None, the tab area itself will be selected (all the windows
        will be deselected). `i_window` is asserted to be non-negative.
        """
        self._tabs[i_tab].current_index = i_window

    def _set_control_widget(self, widget: MockWidget, control: Any | None) -> None:
        """Set the control widget for the given sub window widget.

        A control widget appears on the top-right corner of the toolbar, which will be
        used to display the state of the widget, edit the widget efficiently, etc. For
        example, a font size spinbox for a text editor widget.
        """

    def _update_control_widget(self, current: MockWidget | None) -> None:
        """Switch the control widget to another one in the existing ones.

        If None is given, the control widget will be just hidden.
        """

    def _remove_control_widget(self, widget: MockWidget) -> None:
        """Remove the control widget for the given sub window widget from the stack."""

    def _window_state(self, widget: MockWidget) -> WindowState:
        """The state (min, normal, etc.) of the window."""
        return widget.subwindow._state

    def _set_window_state(
        self,
        widget: MockWidget,
        state: WindowState,
        inst: BackendInstructions,
    ) -> None:
        """Update the state of the window.

        The BackendInstructions indicates the animation or other effects to be applied.
        """
        widget.subwindow._state = state

    def _tab_title(self, i_tab: int) -> str:
        """Get the title of the tab at the index."""
        return self._tabs[i_tab].title

    def _set_tab_title(self, i_tab: int, title: str) -> None:
        """Update the title of the tab at the index."""
        self._tabs[i_tab].title = title

    def _window_title(self, widget: MockWidget) -> str:
        """Get the title of the window."""
        return widget.subwindow._title

    def _set_window_title(self, widget: MockWidget, title: str) -> None:
        """Update the title of the window."""
        widget.subwindow._title = title

    def _window_rect(self, widget: MockWidget) -> WindowRect:
        """Get the rectangle relative to the tab area of the window."""
        return widget.subwindow._rect

    def _set_window_rect(
        self,
        widget: Any,
        rect: WindowRect,
        inst: BackendInstructions,
    ) -> None:
        """Update the rectangle of the window.

        The BackendInstructions indicates the animation or other effects to be applied.
        """
        widget.subwindow._rect = rect

    def _area_size(self) -> tuple[int, int]:
        """Get the size of the tab area."""
        return self.__area_size

    def _open_file_dialog(
        self,
        mode,
        extension_default=None,
        allowed_extensions=None,
        caption=None,
        start_path=None,
    ):
        """Open a file dialog."""
        raise NotImplementedError

    def _request_choice_dialog(
        self,
        title: str,
        message: str,
        choices: list[tuple[str, _T]],
        how: Literal["buttons", "radiobuttons"] = "buttons",
    ) -> _T | None:
        """Request a choice dialog and return the clicked text."""
        raise NotImplementedError

    def _show_command_palette(self, kind: str) -> None:
        """Show the command palette widget of the given kind."""

    def _exit_main_window(self, confirm: bool = False) -> None:
        """Close the main window (confirm if needed)."""

    def _get_widget_list(self, i_tab: int) -> list[tuple[str, MockWidget]]:
        """Get the list of widgets in the tab."""
        return [
            (widget._title, widget._widget) for widget in self._tabs[i_tab].sub_windows
        ]

    def _del_widget_at(self, i_tab: int, i_window: int) -> None:
        """Delete the `i_window`-th window in the `i_tab`-th tab."""
        del self._tabs[i_tab].sub_windows[i_window]

    def _get_tab_name_list(self) -> list[str]:
        """Get the list of tab names."""
        return [tab.title for tab in self._tabs]

    def _del_tab_at(self, i_tab: int) -> None:
        """Delete the `i_tab`-th tab.

        Backend does not need to close the subwindows one by one (will be done on the
        wrapper side).
        """
        del self._tabs[i_tab]

    def _rename_window_at(self, i_tab: int, i_window: int) -> None:
        """Start renaming the `i_window`-th window in the `i_tab`-th tab."""

    def add_widget(self, widget: MockWidget, i_tab: int, title: str) -> MockSubWindow:
        """Add a sub window containing the widget to the tab at the index.

        Return the backend widget.
        """
        sub_window = MockSubWindow(widget, self._tabs[i_tab], title)
        widget.subwindow = sub_window
        self._tabs[i_tab].sub_windows.append(sub_window)
        return sub_window

    def set_widget_as_preview(self, widget: MockWidget):
        """Set the widget state as the preview mode."""

    def add_tab(self, title: str) -> None:
        """Add a empty tab with the title."""
        self._tabs.append(MockTab(title))

    def add_dock_widget(
        self,
        widget: MockWidget,
        title: str | None,
        area: DockAreaString | DockArea | None = DockArea.RIGHT,
        allowed_areas: list[DockAreaString | DockArea] | None = None,
    ) -> MockDockWidget:
        """Add a dock widget containing the widget to the main window.

        Return the backend dock widget.
        """
        dock = MockDockWidget(widget, title or widget.subwindow._title)
        widget.set_dockwidget(dock)
        self._dock_widgets.append(dock)
        return dock

    ### dock widgets ###
    def _dock_widget_visible(self, widget: MockWidget) -> bool:
        """Whether the dock widget is visible."""
        return widget.dockwidget._visible

    def _set_dock_widget_visible(self, widget: MockWidget, visible: bool) -> None:
        """Update the visibility of the dock widget."""
        widget.dockwidget._visible = visible

    def _dock_widget_title(self, widget: MockWidget) -> str:
        """Get the title of the dock widget."""
        return widget.dockwidget.title

    def _set_dock_widget_title(self, widget: MockWidget, title: str) -> None:
        """Update the title of the dock widget."""
        widget.dockwidget.title = title

    def _del_dock_widget(self, widget: MockWidget) -> None:
        """Delete the dock widget."""
        self._dock_widgets.remove(widget.dockwidget)

    ### others ###
    def show(self, run: bool = False) -> None:
        """Show the main window and run the app immediately if `run` is True"""

    def _list_widget_class(
        self,
        type: str,
    ) -> tuple[list[WidgetClassTuple], type[MockModelWrapper]]:
        """List the available widget classes of the given type.

        The method will return (list of (widget model type, widget_class, priority),
        fallback class)
        """
        return [WidgetClassTuple(type, MockModelWrapper)], MockModelWrapper

    def _connect_main_window_signals(self, main_window: MainWindow[MockWidget]):
        """Connect the signal of the backend main window to the callbacks."""

    def _connect_window_events(self, wrapper, backend):
        """Connect the events between the wrapper sub window and the backend widget."""

    def _update_context(self) -> None:
        """Update the application context."""

    def _clipboard_data(self) -> ClipboardDataModel | None:
        """Get the clipboard data."""

    def _set_clipboard_data(self, data: ClipboardDataModel) -> None:
        """Set the clipboard data."""

    def _screenshot(self, target: str):
        """Take a screenshot of the target area."""
        raise NotImplementedError

    def _process_parametric_widget(self, widget):
        """Process a parametric widget so that it can be added to the main window.

        The incoming widget must implements the `get_params` method, which gives the
        dictionary of parameters.
        """
        return widget

    def _connect_parametric_widget_events(
        self,
        wrapper: ParametricWindow,
        widget,
    ) -> None:
        """Connect the events between the wrapper parametric window and the backend."""

    def _signature_to_widget(
        self,
        sig: inspect.Signature,
        show_parameter_labels: bool = True,
        preview: bool = False,
    ) -> MockParametricWidget:
        """Convert a function signature to a widget that can run it."""
        return MockParametricWidget(sig)

    def _add_widget_to_parametric_window(
        self,
        wrapper: ParametricWindow,
        widget,
        result_as: Literal["below", "right"],
    ) -> None:
        """Add a widget to the parametric window."""

    def _remove_widget_from_parametric_window(
        self,
        wrapper: ParametricWindow,
    ) -> None:
        """Remove a widget from the parametric window."""

    def _move_focus_to(self, widget: MockWidget) -> None:
        """Move the focus to the widget."""

    def _set_status_tip(self, tip: str, duration: float) -> None:
        """Set the status tip of the main window for a duration (sec)."""

    def _show_notification(self, text: str, duration: float) -> None:
        """Show notification for a duration (sec)."""

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
        return cb

    def _set_parametric_widget_busy(self, wrapper: ParametricWindow, busy: bool):
        """Set the parametric widget busy status (disable call button etc)."""

    def _add_job_progress(self, future: Future, desc: str, total: int = 0) -> None:
        """Add a job to the job stack."""

    def _add_whats_this(self, text: str, style: Literal["plain", "markdown", "html"]):
        """Add a what's this text to the main window."""
