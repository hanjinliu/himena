from himena import StandardType
from himena.plugins import register_widget_class
from himena_builtins.qt.widgets.dataframe import (
    QDataFrameView,
    QDataFramePlotView,
    DataFrameConfigs,
)

register_widget_class(
    StandardType.DATAFRAME,
    QDataFrameView,
    plugin_configs=DataFrameConfigs(),
    priority=50,
)
register_widget_class(
    StandardType.DATAFRAME_PLOT,
    QDataFramePlotView,
    priority=50,
)
