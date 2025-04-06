from himena.consts import StandardType
from himena.plugins import register_widget_class
from himena_builtins.qt.widgets.array import QArrayView

register_widget_class(StandardType.ARRAY, QArrayView, priority=50)
