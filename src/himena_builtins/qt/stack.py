from himena import StandardType
from himena.plugins import register_widget_class
from himena_builtins.qt.widgets.dict_subtypes import QDataFrameStack, QArrayStack
from himena_builtins.qt.widgets.excel import QExcelEdit

register_widget_class(StandardType.DATAFRAMES, QDataFrameStack, priority=50)
register_widget_class(StandardType.ARRAYS, QArrayStack, priority=50)
register_widget_class(StandardType.EXCEL, QExcelEdit, priority=50)
