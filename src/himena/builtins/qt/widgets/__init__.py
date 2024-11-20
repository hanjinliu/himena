from himena.qt import register_widget
from himena.builtins.qt.widgets.array import QDefaultArrayView
from himena.builtins.qt.widgets.text import QDefaultTextEdit, QDefaultHTMLEdit
from himena.builtins.qt.widgets.table import QDefaultTableWidget
from himena.builtins.qt.widgets.dataframe import QDataFrameView
from himena.builtins.qt.widgets.image import QDefaultImageView
from himena.builtins.qt.widgets.excel import QExcelTableStack
from himena.builtins.qt.widgets.reader_not_found import QReaderNotFoundWidget
from himena.consts import StandardType


def register_default_widget_types() -> None:
    """Register default widget types."""
    register_widget(StandardType.ARRAY, QDefaultArrayView, priority=50)
    register_widget(StandardType.TEXT, QDefaultTextEdit, priority=50)
    register_widget(StandardType.HTML, QDefaultHTMLEdit, priority=50)
    register_widget(StandardType.TABLE, QDefaultTableWidget, priority=50)
    register_widget(StandardType.IMAGE, QDefaultImageView, priority=50)
    register_widget(StandardType.DATAFRAME, QDataFrameView, priority=50)
    register_widget(StandardType.EXCEL, QExcelTableStack, priority=50)
    register_widget(StandardType.READER_NOT_FOUND, QReaderNotFoundWidget, priority=0)


register_default_widget_types()
del register_default_widget_types
