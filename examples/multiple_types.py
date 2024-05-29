from qtpy import QtWidgets as QtW

import re
from royalapp import new_window
from royalapp.types import WidgetDataModel
from royalapp.qt import register_frontend_widget
from royalapp.plugins import get_plugin_interface

APP_NAME = "myapp"

@register_frontend_widget("text")
class MyTextEdit(QtW.QPlainTextEdit):
    def __init__(self, model: WidgetDataModel):
        super().__init__()
        self.setPlainText(model.value)
        self._model = model

    @classmethod
    def from_model(cls, model: WidgetDataModel):
        return cls(model)

    def to_model(self) -> WidgetDataModel:
        return self._model

@register_frontend_widget("html")
class MyHtmlEdit(QtW.QTextEdit):
    def __init__(self, model: WidgetDataModel):
        super().__init__()
        self.setHtml(model.value)
        self._model = model

    @classmethod
    def from_model(cls, model: WidgetDataModel):
        return cls(model)

    def to_model(self) -> WidgetDataModel:
        return self._model

@register_frontend_widget("cannot-save")
class MyNonSavableEdit(QtW.QTextEdit):
    @classmethod
    def from_model(cls, model: WidgetDataModel):
        print("converting model to NonSavableEdit")
        self = cls()
        self.setPlainText(model.value)
        return self

interf = get_plugin_interface(APP_NAME, "my_menu")

@interf.register_function
def to_plain_text(model: WidgetDataModel) -> WidgetDataModel:
    if model.type != "html":
        return None
    new = model.copy()

    pattern = re.compile("<.*?>")
    new.value = re.sub(pattern, "", model.value)
    new.type = "text"
    new.title = model.title + " (plain)"
    return new

@interf.register_function
def to_basic_widget(model: WidgetDataModel) -> WidgetDataModel:
    if model.type != "text":
        return None
    new = model.copy()
    new.type = "cannot-save"
    new.title = model.title + " (cannot save)"
    return new

def main():
    ui = new_window(APP_NAME)
    ui.add_data("<i>Text</i>", type="html", title="test window")
    ui.show(run=True)

if __name__ == "__main__":
    main()
