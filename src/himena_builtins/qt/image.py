from himena import StandardType
from himena.plugins import register_widget_class
from himena_builtins.qt.widgets import _image_commands
from himena_builtins.qt.widgets._image_components import QImageGraphicsView

from himena_builtins.qt.widgets.image import (
    QImageView,
    QImageLabelView,
    ImageViewConfigs,
)
from himena_builtins.qt.widgets._image_components import _roi_items as QtRois

register_widget_class(
    StandardType.IMAGE, QImageView, priority=50, plugin_configs=ImageViewConfigs()
)
register_widget_class(StandardType.IMAGE_LABELS, QImageLabelView, priority=50)

del _image_commands

__all__ = [
    "QImageGraphicsView",
    "QImageView",
    "QImageLabelView",
    "ImageViewConfigs",
    "QtRois",
]
