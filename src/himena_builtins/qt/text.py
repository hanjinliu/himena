from himena import StandardType
from himena.plugins import register_widget_class, register_previewer_class
from himena_builtins.qt.widgets.text import QTextEdit, QRichTextEdit, TextEditConfigs
from himena_builtins.qt.widgets.text_previews import QSvgPreview, QMarkdownPreview

register_widget_class(StandardType.TEXT, QTextEdit, plugin_configs=TextEditConfigs())
register_widget_class(StandardType.HTML, QRichTextEdit)
register_previewer_class(StandardType.SVG, QSvgPreview)
register_previewer_class(StandardType.MARKDOWN, QMarkdownPreview)
