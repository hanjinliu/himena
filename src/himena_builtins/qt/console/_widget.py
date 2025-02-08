from __future__ import annotations

import os
import sys
from pathlib import Path
import weakref
from typing import TYPE_CHECKING
from contextlib import suppress

from qtpy.QtCore import Signal
from qtpy import QtWidgets as QtW, QtGui
from qtconsole.rich_jupyter_widget import RichJupyterWidget
from himena.utils.misc import lru_cache
from himena.qt._utils import get_stylesheet_path
from himena.plugins import validate_protocol

if TYPE_CHECKING:
    from himena.style import Theme
    from himena.widgets import MainWindow
    from himena_builtins.qt.console import ConsoleConfig

    class RichJupyterWidget(RichJupyterWidget, QtW.QWidget):
        """To fix typing problem"""

# Modified from napari_console https://github.com/napari/napari-console

if sys.platform.startswith("win"):
    import asyncio

    try:
        from asyncio import (
            WindowsProactorEventLoopPolicy,
            WindowsSelectorEventLoopPolicy,
        )
    except ImportError:
        pass
        # not affected
    else:
        if type(asyncio.get_event_loop_policy()) is WindowsProactorEventLoopPolicy:
            # WindowsProactorEventLoopPolicy is not compatible with tornado 6
            # fallback to the pre-3.8 default of Selector
            asyncio.set_event_loop_policy(WindowsSelectorEventLoopPolicy())


class QtConsole(RichJupyterWidget):
    """Console widget for the Python interpreter.

    The main window instance is passed to the console as variable `ui` by default.
    Tabs, windows, and the internal data models can be accessed from its attributes.

    ```python
    ui.tabs[0]  # get the first tab instance
    ui.tabs[0][1]  # get the second window in the first tab instance
    ui.current_window  # get the current sub-window instance
    ui.current_model  # get the current data model instance
    ```

    New data can be added to the GUI by its methods.

    ```python
    ui.add_tab()  # add a new tab
    ui.add_data_model(WidgetDataModel(...))  # add a new data model
    ui.add_object(..., type=...)  # add a new python object
    """

    codeExecuted = Signal()

    def __init__(self, ui: MainWindow):
        super().__init__()
        self.setMinimumSize(100, 0)
        self.resize(100, 40)
        self._parent_connected = False
        self._main_window_symbol = "ui"
        self._matplotlib_backend = "inline"
        self._matplotlib_backend_orig = os.environ.get("MPLBACKEND")
        self._ui = ui
        self.codeExecuted.connect(self.setFocus)

    def connect_parent(self):
        from IPython import get_ipython
        from IPython.terminal.interactiveshell import TerminalInteractiveShell
        from ipykernel.connect import get_connection_file
        from ipykernel.inprocess.ipkernel import InProcessInteractiveShell
        from ipykernel.zmqshell import ZMQInteractiveShell
        from qtconsole.client import QtKernelClient
        from qtconsole.inprocess import QtInProcessKernelManager

        if self._parent_connected:
            raise RuntimeError("Console already connected to a window.")
        self._parent_connected = True
        shell = get_ipython()

        if shell is None:
            # If there is no currently running instance create an in-process
            # kernel.
            kernel_manager = QtInProcessKernelManager()
            kernel_manager.start_kernel(show_banner=False)
            kernel_manager.kernel.gui = "qt"

            kernel_client = kernel_manager.client()
            kernel_client.start_channels()

            self.kernel_manager = kernel_manager
            self.kernel_client = kernel_client
            self.shell: InProcessInteractiveShell = kernel_manager.kernel.shell
            self.push = self.shell.push

        elif type(shell) == InProcessInteractiveShell:
            # If there is an existing running InProcessInteractiveShell
            # it is likely because multiple viewers have been launched from
            # the same process. In that case create a new kernel.
            # Connect existing kernel
            kernel_manager = QtInProcessKernelManager(kernel=shell.kernel)
            kernel_client = kernel_manager.client()

            self.kernel_manager = kernel_manager
            self.kernel_client = kernel_client
            self.shell = kernel_manager.kernel.shell
            self.push = self.shell.push

        elif isinstance(shell, TerminalInteractiveShell):
            # if launching from an ipython terminal then adding a console is
            # not supported. Instead users should use the ipython terminal for
            # the same functionality.
            self.kernel_client = None
            self.kernel_manager = None
            self.shell = None
            self.push = lambda var: None

        elif isinstance(shell, ZMQInteractiveShell):
            # if launching from jupyter notebook, connect to the existing
            # kernel
            kernel_client = QtKernelClient(connection_file=get_connection_file())
            kernel_client.load_connection_file()
            kernel_client.start_channels()

            self.kernel_manager = None
            self.kernel_client = kernel_client
            self.shell = shell
            self.push = self.shell.push
        else:
            raise ValueError(f"ipython shell not recognized, got {type(shell)}")

        if self.shell is not None:
            from IPython.paths import get_ipython_dir

            _exit = _get_exit_auto_call()
            _exit.set_main_window(self._ui)
            self.shell.push({"exit": _exit})  # update the "exit"

            # run IPython startup files
            profile_dir = Path(get_ipython_dir()) / "profile_default" / "startup"
            if profile_dir.exists():
                import runpy

                _globals = {}
                for startup in profile_dir.glob("*.py"):
                    with suppress(Exception):
                        _globals.update(runpy.run_path(str(startup)))

                self.shell.push(_globals)

            ns = {self._main_window_symbol: self._ui}
            self.shell.push(ns)

    def execute(self, source=None, hidden=False, interactive=False):
        out = super().execute(source, hidden, interactive)
        self.codeExecuted.emit()
        return out

    def setFocus(self):
        """Set focus to the text edit."""
        self._control.setFocus()
        return None

    def showEvent(self, event):
        """Show event."""
        super().showEvent(event)
        self.setFocus()
        os.environ["MPLBACKEND"] = self._matplotlib_backend
        return None

    def hideEvent(self, a0):
        if self._matplotlib_backend_orig is None:
            del os.environ["MPLBACKEND"]
        else:
            os.environ["MPLBACKEND"] = self._matplotlib_backend_orig
        return super().hideEvent(a0)

    @validate_protocol
    def widget_added_callback(self):
        self.connect_parent()
        QtW.QApplication.processEvents()

    @validate_protocol
    def theme_changed_callback(self, theme: Theme):
        """Update the console theme."""
        # need to set stylesheet via style_sheet property
        self.style_sheet = theme.format_text(get_stylesheet_path().read_text())

        # Set syntax styling and highlighting using theme
        if theme.is_light_background():
            self.syntax_style = "default"
        else:
            self.syntax_style = "native"
        bracket_color = QtGui.QColor(theme.highlight_dim)
        self._bracket_matcher.format.setBackground(bracket_color)

    def update_configs(
        self,
        cfg: ConsoleConfig,
    ):
        old_symbol = self._main_window_symbol
        self._main_window_symbol = cfg.main_window_symbol
        self._matplotlib_backend = cfg.matplotlib_backend
        if self._parent_connected:
            if (ui := self.shell.user_ns.get(old_symbol)) is self._ui:
                self.shell.drop_by_id({old_symbol: ui})
            self.shell.push({self._main_window_symbol: self._ui})


@lru_cache(maxsize=1)
def _get_exit_auto_call():
    from IPython.core.autocall import IPyAutocall

    class ExitAutocall(IPyAutocall):
        """Overwrite the default 'exit' autocall to close the viewer."""

        def __init__(self, ip=None):
            super().__init__(ip)
            self._main = None

        def set_main_window(self, window: MainWindow):
            self._main = weakref.ref(window)

        def __call__(self, *args, **kwargs):
            self._main().close()

    return ExitAutocall()
