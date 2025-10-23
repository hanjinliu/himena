from __future__ import annotations

from contextlib import suppress
import sys
import socket
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Generic, TypeVar
from psygnal import Signal
from himena.exceptions import ExceptionHandler
from himena.widgets import current_instance
from himena.core import new_window
from himena._socket import InterProcessData

if TYPE_CHECKING:
    from IPython import InteractiveShell
    from qtpy.QtWidgets import QApplication
    from warnings import WarningMessage

_A = TypeVar("_A")  # the backend application type


class EventLoopHandler(ABC, Generic[_A]):
    errored = Signal(Exception)
    warned = Signal(object)
    socket_activated = Signal(bytes)
    _instances: dict[str, QtEventLoopHandler] = {}

    def __init__(self, name: str, host: str = "localhost", port: int = 49200):
        self._name = name
        self._instances[name] = self
        self._server_socket: socket.socket | None = None
        self._host: str = host
        self._port: int = port

    @classmethod
    def create(cls, name: str, host: str = "localhost", port: int = 49200):
        if name not in cls._instances:
            cls._instances[name] = QtEventLoopHandler(name, host, port)
        return cls._instances[name]

    @abstractmethod
    def get_app(self) -> _A:
        """Get Application instance."""

    @abstractmethod
    def run_app(self):
        """Start the event loop."""

    def close_socket(self):
        """Close the socket."""
        if self._server_socket:
            with suppress(OSError):
                self._server_socket.shutdown(socket.SHUT_RDWR)
            self._server_socket.close()
            self._server_socket = None

    def process_events(self):
        """Process the GUI events."""


def gui_is_active(event_loop: str) -> bool:
    """True only if "%gui **" magic is called in ipython kernel."""
    shell = get_ipython_shell()
    return shell and shell.active_eventloop == event_loop


class QtEventLoopHandler(EventLoopHandler["QApplication"]):
    _APP: QApplication | None = None

    def get_app(self):
        """Get QApplication."""
        self.gui_qt()
        app = self.instance()
        if app is None:
            app = self.create_application()
        self._APP = app
        return app

    def create_application(self) -> QApplication:
        from qtpy.QtCore import Qt
        from qtpy.QtWidgets import QApplication
        from qtpy import QT6

        if not QT6:
            QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling)
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
        return QApplication([])

    def run_app(self):
        """Start the event loop."""
        if not gui_is_active("qt"):
            with ExceptionHandler(
                hook=self._except_hook,
                warning_hook=self._warn_hook,
            ) as _:
                return self._run_app_routine()
        return self._run_app_routine()

    def process_events(self):
        """Process the Qt events in the main thread."""
        if self._APP is not None:
            self._APP.processEvents()

    def _run_app_routine(self):
        qapp = self.get_app()
        try:
            try:
                self._setup_socket(qapp)
            except PermissionError as e:
                print(e)
            qapp.exec()
        finally:
            self.close_socket()

    def _setup_socket(self, app):
        """Set up a socket for inter-process communication."""
        from qtpy.QtCore import QSocketNotifier

        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server_socket.bind((self._host, self._port))
        self._server_socket.listen(1)
        self._qnotifier = QSocketNotifier(
            self._server_socket.fileno(),
            QSocketNotifier.Type.Read,
            parent=app,
        )
        self._qnotifier.activated.connect(self._on_socket_activated)

    def _on_socket_activated(self, socket: int):
        """Handle socket activation."""

        client_socket, _ = self._server_socket.accept()
        with client_socket:
            chunks = []
            while True:
                chunk = client_socket.recv(1024)
                if not chunk:
                    break
                chunks.append(chunk)
            incoming = b"".join(chunks)
        try:
            data = InterProcessData.from_bytes(incoming)
        except Exception as e:
            print("Failed to parse socket data: %s", e)
            return None
        try:
            ins = current_instance(data.profile_name)
        except KeyError:
            ins = new_window(data.profile_name)
        ins.show()
        for file in data.files:
            ins.read_file(file)

    def instance(self) -> QApplication | None:
        """Get QApplication instance or None if it does not exist."""
        from qtpy.QtWidgets import QApplication

        return QApplication.instance()

    def gui_qt(self) -> None:
        """Call "%gui qt" magic."""
        if not gui_is_active("qt"):
            shell = get_ipython_shell()
            if shell and shell.active_eventloop != "qt":
                shell.enable_gui("qt")
        return None

    def _except_hook(self, exc_type: type[Exception], exc_value: Exception, exc_tb):
        """Exception hook used during application execution."""
        return self.errored.emit(exc_value)

    def _warn_hook(self, warning: WarningMessage):
        """Warning hook used during application execution."""
        return self.warned.emit(warning)


class EmptyEventLoopHandler(EventLoopHandler):
    def get_app(self):
        return None

    def run_app(self):
        return None


def get_event_loop_handler(
    backend: str,
    app_name: str,
    host: str = "localhost",
    port: int = 49200,
) -> EventLoopHandler:
    if backend == "qt":
        return QtEventLoopHandler.create(app_name, host, port)
    else:
        return EmptyEventLoopHandler.create(app_name, host, port)


def get_ipython_shell() -> InteractiveShell | None:
    """Get ipython shell if available."""
    if "IPython" in sys.modules:
        from IPython import get_ipython

        return get_ipython()
    else:
        return None
