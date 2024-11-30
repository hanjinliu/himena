from himena.qt.main_window import MainWindowQt
from himena.qt.registry import register_widget_class
from himena.qt._magicgui import register_magicgui_types
from himena.qt import settings  # just register

__all__ = ["MainWindowQt", "register_widget_class"]

register_magicgui_types()
del register_magicgui_types, settings
