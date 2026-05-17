from himena import StandardType
from himena.plugins import register_widget_class
from himena_builtins.qt.widgets.text import QTextEdit, QRichTextEdit, TextEditConfigs
from himena_builtins.qt.widgets.text_previews import QMarkdownEdit, QSvgView

register_widget_class(StandardType.TEXT, QTextEdit, plugin_configs=TextEditConfigs())
register_widget_class(StandardType.HTML, QRichTextEdit)
register_widget_class(StandardType.SVG, QSvgView)
register_widget_class(StandardType.MARKDOWN, QMarkdownEdit)
