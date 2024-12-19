from qtpy import QtWidgets as QtW

import re
from himena import new_window, WidgetDataModel
from himena.consts import StandardType
from himena.plugins import register_function, register_widget_class

# Register three widget classes that:
# 1. display text as a plain text and can be saved
# 2. display text as an HTML text and can be saved
# 3. display text as a plain text but cannot be saved

@register_widget_class(StandardType.TEXT)
class MyTextEdit(QtW.QPlainTextEdit):
    def update_model(self, model: WidgetDataModel):
        self.setPlainText(model.value)

    def to_model(self) -> WidgetDataModel:
        return WidgetDataModel(value=self.toPlainText(), type=StandardType.TEXT)

@register_widget_class(StandardType.HTML)
class MyHtmlEdit(QtW.QTextEdit):
    def __init__(self, model: WidgetDataModel):
        super().__init__()

    def update_model(self, model: WidgetDataModel):
        self.setHtml(model.value)

    def to_model(self) -> WidgetDataModel:
        return WidgetDataModel(value=self.toHtml(), type=StandardType.HTML)

@register_widget_class("cannot-save")
class MyNonSavableEdit(QtW.QTextEdit):
    def update_model(self, model: WidgetDataModel):
        self.setPlainText(model.value)


@register_function(types=StandardType.HTML, menus=["tools/my_menu"])
def to_plain_text(model: WidgetDataModel) -> WidgetDataModel:
    pattern = re.compile("<.*?>")
    model.value = re.sub(pattern, "", model.value)
    model.type = StandardType.TEXT
    model.title = model.title + " (plain)"
    return model

@register_function(types=[StandardType.TEXT, StandardType.HTML], menus=["tools/my_menu"])
def to_basic_widget(model: WidgetDataModel) -> WidgetDataModel:
    if model.type != StandardType.TEXT:
        return None
    model.type = "cannot-save"
    model.title = model.title + " (cannot save)"
    return model

def main():
    ui = new_window()
    ui.add_object("<i>Text</i>", type="text.html", title="test window")
    ui.show(run=True)

if __name__ == "__main__":
    main()
