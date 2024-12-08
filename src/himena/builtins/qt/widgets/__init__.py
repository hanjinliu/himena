from himena.plugins import register_widget_class
from himena.builtins.qt.widgets.array import QArrayView
from himena.builtins.qt.widgets.text import QTextEdit, QRichTextEdit
from himena.builtins.qt.widgets.table import QSpreadsheet
from himena.builtins.qt.widgets.dataframe import QDataFrameView
from himena.builtins.qt.widgets.image import QImageView
from himena.builtins.qt.widgets.image_rois import QImageRoiView
from himena.builtins.qt.widgets.excel import QExcelFileEdit
from himena.builtins.qt.widgets.ipynb import QIpynbEdit
from himena.builtins.qt.widgets.draw import QDrawCanvas
from himena.builtins.qt.widgets.reader_not_found import QReaderNotFound
from himena.consts import StandardType


def register_default_widget_types() -> None:
    """Register default widget types."""
    register_widget_class(StandardType.ARRAY, QArrayView, priority=50)
    register_widget_class(StandardType.TEXT, QTextEdit, priority=50)
    register_widget_class(StandardType.HTML, QRichTextEdit, priority=50)
    register_widget_class(StandardType.TABLE, QSpreadsheet, priority=50)
    register_widget_class(StandardType.IMAGE, QImageView, priority=50)
    register_widget_class(StandardType.IMAGE_ROIS, QImageRoiView, priority=50)
    register_widget_class(StandardType.IMAGE, QDrawCanvas, priority=0)
    register_widget_class(StandardType.DATAFRAME, QDataFrameView, priority=50)
    register_widget_class(StandardType.EXCEL, QExcelFileEdit, priority=50)
    register_widget_class(StandardType.IPYNB, QIpynbEdit, priority=50)
    register_widget_class(StandardType.READER_NOT_FOUND, QReaderNotFound, priority=0)


register_default_widget_types()
del register_default_widget_types
