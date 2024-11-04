from royalapp.qt import register_frontend_widget
from royalapp.builtins.qt.widgets.text import QDefaultTextEdit, QDefaultHTMLEdit
from royalapp.builtins.qt.widgets.table import QDefaultTableWidget
from royalapp.builtins.qt.widgets.image import QDefaultImageView
from royalapp.consts import StandardTypes


def register_default_widget_types() -> None:
    """Register default widget types."""
    register_frontend_widget("text", QDefaultTextEdit, override=False)
    register_frontend_widget(StandardTypes.TEXT, QDefaultTextEdit, override=False)
    register_frontend_widget("text", QDefaultTextEdit, override=False)
    register_frontend_widget(StandardTypes.HTML, QDefaultHTMLEdit, override=False)
    register_frontend_widget("table", QDefaultTableWidget, override=False)
    register_frontend_widget(StandardTypes.TABLE, QDefaultTableWidget, override=False)
    register_frontend_widget("image", QDefaultImageView, override=False)
    register_frontend_widget(StandardTypes.IMAGE, QDefaultImageView, override=False)


register_default_widget_types()
del register_default_widget_types
