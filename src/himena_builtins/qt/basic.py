from himena import StandardType
from himena.plugins import register_widget_class

from himena_builtins.qt.widgets.dataframe import QDictView
from himena_builtins.qt.widgets.model_stack import QModelStack
from himena_builtins.qt.widgets.reader_not_found import QReaderNotFound
from himena_builtins.qt.widgets.function import QFunctionEdit
from himena_builtins.qt.widgets.workflow import QWorkflowView

register_widget_class(StandardType.FUNCTION, QFunctionEdit, priority=50)
register_widget_class(StandardType.MODELS, QModelStack, priority=50)
register_widget_class(StandardType.WORKFLOW, QWorkflowView, priority=50)
register_widget_class(StandardType.READER_NOT_FOUND, QReaderNotFound, priority=0)
register_widget_class(StandardType.DICT, QDictView, priority=10)


def _pdf_viewer():
    # NOTE: Qt5 does not implement QtPdfWidgets.
    from himena_builtins.qt.widgets.pdf import QPdfViewer

    return QPdfViewer()


_pdf_viewer.__himena_widget_id__ = "builtins:QPdfViewer"
_pdf_viewer.__himena_display_name__ = "Built-in PDF Viewer"

register_widget_class(StandardType.PDF, _pdf_viewer, priority=10)
