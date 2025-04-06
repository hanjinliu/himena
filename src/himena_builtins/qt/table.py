from himena import StandardType
from himena.plugins import register_widget_class
from himena_builtins.qt.widgets.table import QSpreadsheet, SpreadsheetConfigs

register_widget_class(
    StandardType.TABLE, QSpreadsheet, plugin_configs=SpreadsheetConfigs()
)
