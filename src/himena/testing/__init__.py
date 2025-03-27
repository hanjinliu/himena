"""Test consistency and completeness of frontend widget implementations.

This submodule provides a set of helper functions to test the widget implementations.
Note that they are not meant to test the GUI, but the logic of `update_model` and
`to_model` methods of the widgets.
"""

from himena.testing import image, table
from himena.testing.subwindow import WidgetTester
from himena.testing._pytest import install_plugin
from himena.testing.dialog import file_dialog_response, choose_one_dialog_response

__all__ = [
    "image",
    "table",
    "WidgetTester",
    "install_plugin",
    "file_dialog_response",
    "choose_one_dialog_response",
]
