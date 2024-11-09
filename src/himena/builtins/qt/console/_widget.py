from __future__ import annotations

from pathlib import Path
import weakref
from typing import TYPE_CHECKING
from contextlib import suppress

from qtpy.QtCore import Signal
from qtpy import QtWidgets as QtW
from qtconsole.rich_jupyter_widget import RichJupyterWidget
from himena._utils import lru_cache

if TYPE_CHECKING:
    from himena.widgets import MainWindow

    class RichJupyterWidget(RichJupyterWidget, QtW.QWidget):
        """To fix typing problem"""


# Modified from napari_console https://github.com/napari/napari-console
class QtConsole(RichJupyterWidget):
    codeExecuted = Signal(str)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setMinimumSize(100, 0)
        self.resize(100, 40)
        self._parent_connected = False
        self.codeExecuted.connect(self.setFocus)

    def connect_parent(self, window: MainWindow):
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
            _exit.set_main_window(window)
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

            ns = {"ui": window}
            self.shell.push(ns)

    def setFocus(self):
        """Set focus to the text edit."""
        self._control.setFocus()
        return None

    def showEvent(self, event):
        """Show event."""
        super().showEvent(event)
        self.setFocus()
        return None


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
