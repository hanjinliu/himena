from functools import partial
from himena.plugins import register_widget_class, register_previewer_class
from himena_builtins.qt.widgets.array import QArrayView
from himena_builtins.qt.widgets.text import QTextEdit, QRichTextEdit, TextEditConfigs
from himena_builtins.qt.widgets.table import QSpreadsheet, SpreadsheetConfigs
from himena_builtins.qt.widgets.dataframe import (
    QDataFrameView,
    QDataFramePlotView,
    DataFrameConfigs,
)
from himena_builtins.qt.widgets.dict_subtypes import QDataFrameStack, QArrayStack
from himena_builtins.qt.widgets.image import (
    QImageView,
    QImageLabelView,
    ImageViewConfigs,
)
from himena_builtins.qt.widgets.image_rois import QImageRoiView
from himena_builtins.qt.widgets.excel import QExcelEdit
from himena_builtins.qt.widgets.ipynb import QIpynbEdit
from himena_builtins.qt.widgets.text_previews import QSvgPreview, QMarkdowPreview
from himena_builtins.qt.widgets.model_stack import QModelStack
from himena_builtins.qt.widgets.reader_not_found import QReaderNotFound
from himena_builtins.qt.widgets.function import QFunctionEdit
from himena_builtins.qt.widgets.workflow import QWorkflowView
from himena.consts import StandardType


def register_default_widget_types() -> None:
    """Register default widget types."""

    from himena_builtins.qt.widgets import _commands

    del _commands
    _register = partial(register_widget_class, priority=50)

    # text
    _register(StandardType.TEXT, QTextEdit, plugin_configs=TextEditConfigs())
    _register(StandardType.HTML, QRichTextEdit)
    _register(StandardType.IPYNB, QIpynbEdit)

    # table
    _register(StandardType.TABLE, QSpreadsheet, plugin_configs=SpreadsheetConfigs())

    # array
    _register(StandardType.ARRAY, QArrayView)
    _register(StandardType.IMAGE_LABELS, QImageLabelView)
    _register(StandardType.IMAGE, QImageView, plugin_configs=ImageViewConfigs())

    # dataframe
    _register(StandardType.DATAFRAME, QDataFrameView, plugin_configs=DataFrameConfigs())
    _register(StandardType.DATAFRAME_PLOT, QDataFramePlotView)

    _register(StandardType.DATAFRAMES, QDataFrameStack)
    _register(StandardType.ARRAYS, QArrayStack)

    # others
    _register(StandardType.ROIS, QImageRoiView)
    _register(StandardType.EXCEL, QExcelEdit)
    _register(StandardType.MODELS, QModelStack)
    _register(StandardType.FUNCTION, QFunctionEdit)
    _register(StandardType.WORKFLOW, QWorkflowView)

    register_widget_class(StandardType.READER_NOT_FOUND, QReaderNotFound, priority=0)
    register_previewer_class(StandardType.SVG, QSvgPreview)
    register_previewer_class(StandardType.MARKDOWN, QMarkdowPreview)


register_default_widget_types()
del register_default_widget_types
