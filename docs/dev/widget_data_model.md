# The WidgetDataMode Standard

All the widgets in `himena` are built on the `WidgetDataModel` standard. A
`WidgetDataModel` is a Python object that represents a value of any type, tagged with
some additional information of how to interpret the value in GUI. For example, a text
data "xyz" read from a txt file can be written as follows:

``` python
WidgetDataModel(value="abc", type="text")
```

All the widgets in `himena` implements `update_model()` method to update the state of
the widget from a `WidgetDataModel` object, and `to_model()` method to dump the state
of the widget to a `WidgetDataModel` object.

``` python
class TextViewer:
    def __init__(self):
        # some GUI-specific initialization ...

    def update_model(self, model: WidgetDataModel):
        self.set_text(model.value)

    def to_model(self) -> WidgetDataModel:
        return WidgetDataModel(value=self.get_text(), type="text")
```

And this widget is registered as a widget that represents a `"text"`-type data using
`register_widget_class()` function.

``` python
from himena.plugins import register_widget_class

register_widget_class("text", widget_class=TextViewer)
```

The `WidgetDataModel` standard makes the different part of development very clear-cut.

- Reader function is a **GUI-independent** function that reads a file and returns
  a `WidgetDataModel`.

    ``` python
    def read_txt(file_path: Path) -> WidgetDataModel:
        text_value = file_path.read_text()
        return WidgetDataModel(value=text_value, type="text")
    ```

  A proper widget class will be automatically selected based on the `type` field, and
  updated based on the returned model using `update_model()` method.

- Writer function is a **GUI-independent** function that writes a `WidgetDataModel`
  to a file.

    ``` python
    def write_text(file_path: Path, model: WidgetDataModel):
        file_path.write_text(model.value)
    ```

  A widget will be automatically converted to a model using `to_model()` method  before
  calling this writer function.

- Any function for data processing or analysis is also **GUI-independent** functions
  that just convert a `WidgetDataModel` into another.

    ``` python
    def to_upper(model: WidgetDataModel) -> WidgetDataModel:
        assert isinstance(model.value, str)
        return WidgetDataModel(value=model.value.upper(), type="text")
    ```

  A widget will be automatically converted to a model using `to_model()` method before
  calling this function, and sent back to the GUI as another widget created based on the
  returned model.

    ``` mermaid
    flowchart LR
        widget0([Widget A])
        widget1([Widget B])
        model0[[WidgetDataModel A]]
        model1[[WidgetDataModel B]]
        widget0 --> model0 == to_upper() ==> model1 --> widget1
    ```

!!! note

    You can use any string for `type` field, but make your widget interpretable for
    the `himena` built-in functions and probably for other plugins, you may want to
    use the `StandardType`.

    ``` python
    from himena.const import StandardType

    StandardType.TEXT  # "text"
    StandardType.TABLE  # "table"
    StandardType.ARRAY  # "array"
    StandardType.IMAGE  # "array.image"
    ```

    For the detail, see the [Model Types](./model_types.md) section.

## More Specifications

You can set other fields of `WidgetDataModel` to provide more details of how to convert
the data to a widget.

``` python
WidgetDataModel(
    value="abc",
    type="text",
    title="My Text"  # title of the widget
    extension_default=".txt",  # default file extension in the save dialog
    extensions=[".txt", ".md"]  # allowed file extensions in the save dialog
)
```
