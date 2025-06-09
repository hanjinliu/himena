# Drag and Drop

Implementation of drag and drop is indispensable for a good user experience of a plugin
widget. Currently, Qt is the only supported GUI framework, and Qt provides overriddable
methods for drag and drop; therefore, you can just define the behavior at the widget
level. However, low-level implementation of drag and drop ignores the rich functionality
of `himena`, especially the [workflow](../usage/workflows.md). This section describes
how to implement drag and drop nicely.

## Drag a Command and Associated Parameters

In `himena`, dragging a part of the widget is more like dragging a set of command and
associated parameters. The command is supposed to be executed when the user drops it.

To do this, you need to first register a command, and call `drag_command` method
when the user starts dragging. Because mouse dragging event can only handled at the Qt
level, you usually need to override the `mouseMoveEvent` methods to trigger a drag.

#### 1. Register a command

First, you need to register a command that will be executed when the user drops the
item. The way you register a command is exactly the same as [registering any other commands](register_functions.md).

Following is an example of registering a command that just creates a text data.

```python
from himena import WidgetDataModel, Parametric, StandardType
from himena.plugins import register_hidden_function

@register_hidden_function(command_id="test-drag")
def test_drag() -> Parametric:
    def run(text: str) -> WidgetDataModel:
        return WidgetDataModel(value=text, type=StandardType.TEXT)
    return run
```

#### 2. Implement a widget

`drag_command` must be called when dragging starts. It takes parameters that specify
the `QDrag` source object, resulting type, command to be executed, and associated
parameters. `command_id` and `with_params` work similarly as the `exec_action` method of
the main window.

Following is a simple widget that starts dragging event when the user moves the mouse
while holding the right button.

```python
from qtpy import QtCore, QtGui, QtWidgets as QtW
from himena.qt import drag_command

class MyWidget(QtW.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_dragging = False

    def mouseMoveEvent(self, a0):
        if self._is_dragging:
            return super().mouseMoveEvent(a0)
        if a0.buttons() & QtCore.Qt.MouseButton.RightButton:
            self._is_dragging = True
            drag_command(
                source=self,
                type=StandardType.TEXT,
                command_id="test-drag",
                with_params={"text": "TEST DRAG"},
                desc="Testing Drag ...",
            )
            return
        return super().mouseMoveEvent(a0)

    def mouseReleaseEvent(self, a0: QtGui.QMouseEvent | None) -> None:
        self._is_dragging = False
        return super().mouseReleaseEvent(a0)

```

#### 3. Test it!

Now, you can test the drag and drop functionality by directly adding the widget to the
main window.

```python
from himena import new_window

ui = new_window()
ui.add_widget(MyWidget())
ui.show()
```
