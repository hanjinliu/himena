from himena import StandardType
from himena.plugins import register_widget_class

from himena_builtins.qt.widgets.dataframe import QDictView
from himena_builtins.qt.widgets.model_stack import QModelStack
from himena_builtins.qt.widgets.reader_not_found import QReaderNotFound
from himena_builtins.qt.widgets.function import QFunctionEdit
from himena_builtins.qt.widgets.pdf import QPdfViewer
from himena_builtins.qt.widgets.workflow import QWorkflowView

register_widget_class(StandardType.FUNCTION, QFunctionEdit, priority=50)
register_widget_class(StandardType.MODELS, QModelStack, priority=50)
register_widget_class(StandardType.WORKFLOW, QWorkflowView, priority=50)
register_widget_class(StandardType.READER_NOT_FOUND, QReaderNotFound, priority=0)
register_widget_class(StandardType.DICT, QDictView, priority=10)
register_widget_class(StandardType.PDF, QPdfViewer, priority=10)
