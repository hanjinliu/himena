from qtpy import QtWidgets as QtW

import re
from himena import new_window, WidgetDataModel
from himena.qt import register_widget
from himena.plugins import register_function


@register_widget("text")
class MyTextEdit(QtW.QPlainTextEdit):
    def update_model(self, model: WidgetDataModel):
        self.setPlainText(model.value)

    def to_model(self) -> WidgetDataModel:
        return WidgetDataModel(value=self.toPlainText(), type="text")

@register_widget("html")
class MyHtmlEdit(QtW.QTextEdit):
    def __init__(self, model: WidgetDataModel):
        super().__init__()

    def update_model(self, model: WidgetDataModel):
        self.setHtml(model.value)

    def to_model(self) -> WidgetDataModel:
        return WidgetDataModel(value=self.toHtml(), type="text.html")

@register_widget("cannot-save")
class MyNonSavableEdit(QtW.QTextEdit):
    def update_model(self, model: WidgetDataModel):
        self.setPlainText(model.value)


@register_function(types="html", menus=["tools/my_menu"])
def to_plain_text(model: WidgetDataModel) -> WidgetDataModel:
    pattern = re.compile("<.*?>")
    model.value = re.sub(pattern, "", model.value)
    model.type = "text"
    model.title = model.title + " (plain)"
    return model

@register_function(types=["text", "html"], menus=["tools/my_menu"])
def to_basic_widget(model: WidgetDataModel) -> WidgetDataModel:
    if model.type != "text":
        return None
    model.type = "cannot-save"
    model.title = model.title + " (cannot save)"
    return model

def main():
    ui = new_window()
    ui.add_data("<i>Text</i>", type="text.html", title="test window")
    ui.show(run=True)

if __name__ == "__main__":
    main()
