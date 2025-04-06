from himena import StandardType
from himena.plugins import register_widget_class
from himena_builtins.qt.widgets.ipynb import QIpynbEdit

register_widget_class(StandardType.IPYNB, QIpynbEdit, priority=50)
