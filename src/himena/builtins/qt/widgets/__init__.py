from himena.plugins import register_widget_class
from himena.builtins.qt.widgets.array import QDefaultArrayView
from himena.builtins.qt.widgets.text import QDefaultTextEdit, QDefaultRichTextEdit
from himena.builtins.qt.widgets.table import QDefaultTableWidget
from himena.builtins.qt.widgets.dataframe import QDataFrameView
from himena.builtins.qt.widgets.image import QDefaultImageView
from himena.builtins.qt.widgets.excel import QExcelTableStack
from himena.builtins.qt.widgets.reader_not_found import QReaderNotFoundWidget
from himena.consts import StandardType


def register_default_widget_types() -> None:
    """Register default widget types."""
    register_widget_class(StandardType.ARRAY, QDefaultArrayView, priority=50)
    register_widget_class(StandardType.TEXT, QDefaultTextEdit, priority=50)
    register_widget_class(StandardType.HTML, QDefaultRichTextEdit, priority=50)
    register_widget_class(StandardType.TABLE, QDefaultTableWidget, priority=50)
    register_widget_class(StandardType.IMAGE, QDefaultImageView, priority=50)
    register_widget_class(StandardType.DATAFRAME, QDataFrameView, priority=50)
    register_widget_class(StandardType.EXCEL, QExcelTableStack, priority=50)
    register_widget_class(
        StandardType.READER_NOT_FOUND, QReaderNotFoundWidget, priority=0
    )


register_default_widget_types()
del register_default_widget_types
