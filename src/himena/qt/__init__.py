from himena.qt.main_window import MainWindowQt
from himena.qt.registry import register_widget
from himena.qt._magicgui import register_magicgui_types

__all__ = ["MainWindowQt", "register_widget"]

register_magicgui_types()
del register_magicgui_types
