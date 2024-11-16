from himena.qt import register_widget
from himena.builtins.qt.widgets.array import QDefaultArrayView
from himena.builtins.qt.widgets.text import QDefaultTextEdit, QDefaultHTMLEdit
from himena.builtins.qt.widgets.table import QDefaultTableWidget
from himena.builtins.qt.widgets.dataframe import QDataFrameView
from himena.builtins.qt.widgets.image import QDefaultImageView
from himena.builtins.qt.widgets.excel import QExcelTableStack
from himena.consts import StandardType, StandardSubtype


def register_default_widget_types() -> None:
    """Register default widget types."""
    register_widget(StandardType.ARRAY, QDefaultArrayView, priority=-1)
    register_widget(StandardType.TEXT, QDefaultTextEdit, priority=-1)
    register_widget(StandardSubtype.HTML, QDefaultHTMLEdit, priority=-1)
    register_widget(StandardType.TABLE, QDefaultTableWidget, priority=-1)
    register_widget(StandardSubtype.IMAGE, QDefaultImageView, priority=-1)
    register_widget(StandardType.DATAFRAME, QDataFrameView, priority=-1)
    register_widget(StandardType.EXCEL, QExcelTableStack, priority=-1)


register_default_widget_types()
del register_default_widget_types
