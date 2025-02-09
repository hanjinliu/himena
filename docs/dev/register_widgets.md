# Register Widgets

## Protocols

To avoid the potential dangers of metaclass collision and method collision, `himena` do
not use a super class to define plugin widgets. Instead, your plugin widgets have to
implement protocols (methods with correct name and arguments) to enable the
communication between the plugin and the main application.

??? tip "Check misspelling"

    Because the plugin widgets do not inherit anything like plugin classes, you have to
    be careful not to misspell the method name. To check if the method name is correct,
    you can decorate the protocol methods with `validate_protocol` decorator.

    ``` python hl_lines="4"
    from himena.plugins import validate_protocol

    class MyWidget:
        @validate_protocol
        def udpate_model(self, model):  # misspelled, raises error
            ...
    ```

All the protocols are optional, but to make the plugin better, you should implement as
many protocols as possible.

### Compatibility with `WidgetDataModel` Standard

To make the plugin widgets compatible with the `WidgetDataModel` standard that is used
everywhere in `himena`, you have to implement the following protocols:

- `update_model(self, model: WidgetDataModel) -> None`: Update the widget state based
  on the model.
- `to_model(self) -> WidgetDataModel`: Return the model that represents the current
  state of the widget.
- `model_type(self) -> str`: Return the type of the model that the widget uses. Model
  type is frequently checked in many occasions, so you should implement this method if
  `to_model` is computationally expensive.
- `update_value(self, value: Any) -> None`: Update the widget state based on the value
  without changing the states that are described by the `metadata` field of the
  `WidgetDataModel`. This method is preferentially called by the `update_value` method
  of `SubWindow` class.


### Control Widget

The [control widget](../usage/basics.md#appearance) is a widget that is added to the
tool bar of the main window to make the sub-window area tidy. This widget can be defined
by implementing the following protocol.

- `control_widget(self) -> <backend widget type>`: Construct and return the control
  widget.

The return type must be interpretable by the backend GUI library. For example, if your
plugin widget is implemented using `Qt`, the return type should be a `QWidget` object
as well.

### Use Wrapper Class

Python already has a lot of libraries that wrap other GUI libraries to provide better
interface. In `himena`, you can directly use these wrapper classes and implement all the
protocols on the wrapper class. In this case, you will have to tell where the backend
widget is located, which can be done by implementing the following protocol.

- `native_widget(self) -> <backend widget type>`: Return the backend widget that is
  wrapped by the wrapper class.

### Widget Interactivity

Widgets can be interactively modified by the user. To change the interactivity, or to
programmatically mark the widget as modified, you can implement the following protocols.

- `is_editable(self) -> bool`: Return whether the widget is editable or not.
- `set_editable(self, editable: bool) -> None`: Set the widget editable or not.
- `is_modified(self) -> bool`: Return whether the underlying data is modified or not.
- `set_modified(self, modified: bool) -> None`: Set the modified state of the widget.

### Response to the GUI Events

Sometimes your widget needs to catch the GUI events to update the widget state.

- `theme_changed_callback(self, theme: Theme) -> None`: Called when the theme of the
  application is changed. The `Theme` object is a data class that contains the color
  theme of the application.
- `widget_added_callback(self) -> None`: Called when the sub-window containing this
  widget is added to the main window.
- `widget_activated_callback(self) -> None`: Called when the sub-window containing this
  widget is activated (clicked or focus).
- `widget_closed_callback(self) -> None`:  Called when the sub-window containing this
  widget is closed.
- `widget_resized_callback(self, old_size: Size, new_size: Size) -> None`: Called when
  the sub-window containing this widget is resized from the old size to a new size.
  [`Size`][himena.types.Size] is a tuple like object with `width` and `height` fields.

### Drag and Drop

Drag-and-drop operation is handled using [`DragDropModel`][himena.types.DragDropModel].

- `dropped_callback(self, model: DragDropModel) -> None`: Callback method when an item
  is dropped on the widget.
- `allowed_drop_types(self) -> list[str]`: List of types that the widget accepts.

### Widget Appearance

- `size_hint(self) -> tuple[int, int]`: Return the size hint of the widget. This method
  is called when the widget is added to the main window.
- `default_title(self) -> str`: Return the default title of the widget. This method is
  called when the widget is added to the main window without specifying the title.

## Register the Widget

``` python
from qtpy import QtWidgets as QtW
from himena.plugins import validate_protocol

class MyWidget(QtW.QTextEdit):
    def __init__(self):
        super().__init__()

    @validate_protocol
    def update_model(self, model):
        assert model.type == "text"
        self.setPlainText(model.value)

    @validate_protocol
    def to_model(self):
        return WidgetDataModel(value=self.toPlainText(), type="text")

    @validate_protocol
    def size_hint(self):
        return 400, 300
```

Once you have implemented the protocols like above, you can register the widget class
using the `register_widget_class` function.

``` python
from himena import StandardType
from himena.plugins import register_widget_class

register_widget_class(StandardType.TEXT, MyWidget)
```

The first argument is the type of the data the widget class is supposed to handle.
Whenever the application is requested to add a data model of that type, this widget will
be constructed like below:

``` python
widget = MyWidget()
widget.update_model(model)
```

and added to the main window inside a sub-window.

??? tip "Register function instead of class"

    Because what is done here is just calling the constructor of the widget class, the
    object registered by the `register_widget_class` function does not have to be a
    class. You can also register a function that returns the widget object.

    ``` python
    def create_widget():
        return MyWidget()

    register_widget_class(StandardType.TEXT, create_widget)
    ```

    This is useful when you want to execute the file that defines the widget class
    lazily, in order to reduce the startup time of the application.
