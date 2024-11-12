from himena.qt import register_frontend_widget
from himena.builtins.qt.widgets.text import QDefaultTextEdit, QDefaultHTMLEdit
from himena.builtins.qt.widgets.table import QDefaultTableWidget
from himena.builtins.qt.widgets.image import QDefaultImageView
from himena.consts import StandardTypes, StandardSubtypes


def register_default_widget_types() -> None:
    """Register default widget types."""
    register_frontend_widget(StandardTypes.TEXT, QDefaultTextEdit, priority=-1)
    register_frontend_widget(StandardSubtypes.HTML, QDefaultHTMLEdit, priority=-1)
    register_frontend_widget(StandardTypes.TABLE, QDefaultTableWidget, priority=-1)
    register_frontend_widget(StandardTypes.IMAGE, QDefaultImageView, priority=-1)


register_default_widget_types()
del register_default_widget_types
