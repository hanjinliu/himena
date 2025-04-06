from himena import StandardType
from himena.plugins import register_widget_class
from himena_builtins.qt.widgets import _image_commands


from himena_builtins.qt.widgets.image import (
    QImageView,
    QImageLabelView,
    ImageViewConfigs,
)

register_widget_class(
    StandardType.IMAGE, QImageView, priority=50, plugin_configs=ImageViewConfigs()
)
register_widget_class(StandardType.IMAGE_LABELS, QImageLabelView, priority=50)

del _image_commands
