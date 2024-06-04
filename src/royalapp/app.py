from __future__ import annotations

import sys
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from IPython import InteractiveShell
    from qtpy.QtWidgets import QApplication


class EventLoopHandler(ABC):
    def __init__(self, name: str):
        self._name = name

    @abstractmethod
    def get_app(self) -> Any:
        """Get Application."""

    @abstractmethod
    def run_app(self):
        """Start the event loop."""


def gui_is_active(event_loop: str) -> bool:
    """True only if "%gui **" magic is called in ipython kernel."""
    shell = get_ipython_shell()
    return shell and shell.active_eventloop == event_loop


class QtEventLoopHandler(EventLoopHandler):
    _APP: QApplication | None = None

    def get_app(self):
        """Get QApplication."""
        self.gui_qt()
        app = self.instance()
        if app is None:
            app = self.create_application()
        self._APP = app
        return app

    def create_application(self):
        from qtpy.QtCore import Qt
        from qtpy.QtWidgets import QApplication

        QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling)
        return QApplication([])

    def run_app(self):
        """Start the event loop."""
        if not gui_is_active("qt"):
            from tabulous.exceptions import ExceptionHandler

            with ExceptionHandler(hook=self._excepthook) as _:
                self.get_app().exec_()
            return None

        return self.get_app().exec_()

    def instance(self):
        from qtpy.QtWidgets import QApplication

        return QApplication.instance()

    def gui_qt(self):
        """Call "%gui qt" magic."""
        if not gui_is_active("qt"):
            shell = get_ipython_shell()
            if shell and shell.active_eventloop != "qt":
                shell.enable_gui("qt")
        return None

    def _excepthook(self, exc_type: type[Exception], exc_value: Exception, exc_tb):
        """Exception hook used during application execution."""
        from royalapp.qt._qtraceback import QtErrorMessageBox
        from royalapp.widgets._main_window import current_instance

        viewer = current_instance(self._name)
        QtErrorMessageBox.raise_(exc_value, parent=viewer._backend_main_window)
        return None


class EmptyEventLoopHandler(EventLoopHandler):
    def get_app(self):
        return None

    def run_app(self):
        return None


def get_event_loop_handler(backend: str, app_name: str) -> EventLoopHandler:
    if backend == "qt":
        return QtEventLoopHandler(app_name)
    else:
        return EmptyEventLoopHandler(app_name)


def get_ipython_shell() -> InteractiveShell | None:
    """Get ipython shell if available."""
    if "IPython" in sys.modules:
        from IPython import get_ipython

        return get_ipython()
    else:
        return None
