from himena import StandardType
from himena.plugins import register_widget_class
from himena_builtins.qt.widgets.image_rois import QImageRoiView

register_widget_class(StandardType.ROIS, QImageRoiView, priority=50)
