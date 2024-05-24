from __future__ import annotations

import sys
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from IPython import InteractiveShell
    from qtpy.QtWidgets import QApplication


class Application(ABC):
    @abstractmethod
    def get_app(self):
        """Get Application."""

    @abstractmethod
    def run_app(self):
        """Start the event loop."""


class QtApplication(Application):
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
        return self.get_app().exec_()

    def instance(self):
        from qtpy.QtWidgets import QApplication

        return QApplication.instance()

    def gui_qt(self):
        """Call "%gui qt" magic."""
        shell = get_shell()

        if shell and shell.active_eventloop != "qt":
            shell.enable_gui("qt")
        return None


class EmptyApplication(Application):
    def get_app(self):
        return None

    def run_app(self):
        return None

def get_app(name: str) -> Application:
    if name == "qt":
        return QtApplication()
    else:
        return EmptyApplication()


def get_shell() -> InteractiveShell | None:
    """Get ipython shell if available."""
    if "IPython" in sys.modules:
        from IPython import get_ipython

        return get_ipython()
    else:
        return None
