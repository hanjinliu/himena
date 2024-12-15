from magicgui.widgets import Container, LineEdit, SpinBox
from himena import new_window, WidgetDataModel
from himena.plugins import register_widget_class, protocol_override, register_function

# Himena natively supports magicgui widgets as a interface of the widgets.
# The himena protocols, such as update_model and to_model, can be implemented on the
# magicgui widgets. The following example demonstrates how to use magicgui widgets as
# a plugin in Himena.

INT_STR = "int_str"  # type of the model

@register_widget_class(INT_STR)
class IntStrView(Container):
    def __init__(self):
        self._int = SpinBox()
        self._str = LineEdit()
        super().__init__(widgets=[self._int, self._str])

    @protocol_override
    def update_model(self, model: WidgetDataModel):
        v0, v1 = model.value
        self._int.value = v0
        self._str.value = v1

    @protocol_override
    def to_model(self) -> WidgetDataModel:
        return WidgetDataModel(value=(self._int.value, self._str.value), type=INT_STR)

    @protocol_override
    def model_type(self) -> str:
        return INT_STR

@register_function(
    title="increment",
    types=INT_STR,
)
def increment(model: WidgetDataModel) -> WidgetDataModel:
    return WidgetDataModel(
        value=(model.value[0] + 1, model.value[1]),
        type=INT_STR,
        title=model.title + " +1",
    )

if __name__ == "__main__":
    ui = new_window()
    ui.add_data((42, "hello"), type=INT_STR, title="test window")
    ui.show(run=True)
