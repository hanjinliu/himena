from royalapp.qt.main_window import MainWindowQt
from royalapp.qt.registry import register_frontend_widget
from royalapp.qt._magicgui import register_magicgui_types

__all__ = ["MainWindowQt", "register_frontend_widget"]

register_magicgui_types()
del register_magicgui_types
