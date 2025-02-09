# Tab/Window Manipulation

The current state of the application can be programmatically manipulated by using the
`ui` variable.

## Access to Tabs and Sub-windows

`ui.tabs` is a list-like object that contains all the tab. Each tab is another list-like
objects that contains all the sub-windows.

``` python
ui.tabs[0]  # The first tab
```

``` title="Output Example"
TabArea([
  SubWindow(title='Table-0', widget=<builtins:QSpreadsheet>),
  SubWindow(title='Untitled-1', widget=<builtins:QTextEdit>),
])
```

``` python
ui.tabs[0][1]  # The second sub-window in the first tab
```

``` title="Output Example"
SubWindow(title='Untitled-1', widget=<builtins:QTextEdit>)
```

Currently active tab and sub-window can be accessed by followign properties.

``` python
ui.tabs.current_index  # The index of the current tab
ui.tabs[0].current_index  # The index of the current sub-window in the first tab
```

There are shortcut methods to access the current sub-window and the underlying data
model.

``` python
ui.current_window  # The current sub-window
ui.current_model  # The current data model
```

## Adding Tabs and Sub-windows

To add a new tab, use `ui.add_tab` method.

``` python
ui.add_tab()
ui.add_tab("new tab")  # with a name
```

Both main window and tab have methods of same names to add sub-windows. If a method is
called from the main window, sub-window will be added to the current tab, or to a new
tab if there is no tab.

``` python
# add array object to the current tab
ui.add_object(np.arange(10), type="array", title="my array")

# add array object to the current tab
ui.tabs[0].add_object(np.arange(10), type="array", title="my array")

# add a WidgetDataModel
model = WidgetDataModel(value=np.arange(10), type="array", title="my array")
ui.add_data_model(model)

# add any Qt widget
from qtpy.QtWidgets import QPushButton

ui.add_widget(QPushButton("Hello, world!"))

# add a magicgui widget
from magicgui.widgets import LineEdit

ui.add_magicgui(LineEdit(name="name", value="abc"))
```

## Access to the Data and Widget States

Basically, the sub-window state is obtained by a `WidgetDataModel`.

``` python
win = ui.add_object("abc", type="text", title="my text")
model = win.to_model()  # a WidgetDataModel object
model.value  # "abc"
```

Widget states that are irrelevant to the data are stored in the `metadata` property.
The type of this property differs between data types, and sometimes, widget types. In
the case of text data, `TextMeta` object is used in the default widget.

``` python
model.metadata
```

``` title="Output"
TextMeta(
  language='Plain Text',
  spaces=4,
  selection=(0, 0),
  font_family='Consolas',
  font_size=10.0,
  encoding='utf-8',
)
```

## Closing Tabs and Sub-windows

Tabs and sub-windows can be closed by `del`.

``` python
del ui.tabs[0]  # close the first tab
del ui.tabs[0][1]  # close the second sub-window in the first tab
```

## Resizing and Moving Sub-windows

The geometry of sub-windows can be manipulated by `rect` property. It is a tuple-like
[`WindowRect`][himena.types.WindowRect] object.

``` python
win = ui.current_window
win.rect
```

``` title="Output"
WindowRect(left=28, top=28, width=400, height=300)
```

``` python
win.rect = (50, 40, 200, 250)  # update the geometry
```

If you only want to resize the window, you can use the `size` property.

``` python
win.size = (200, 250)  # resize the window
```

To move sub-windows, `WindowRect` object has several useful methods.

- `move_top_left`
- `move_top_right`
- `move_bottom_left`
- `move_bottom_right`

These methods return a new `WindowRect` object with updated positions.

``` python
win.rect = win.rect.move_top_left(10, 20)
win.rect
```

``` title="Output"
WindowRect(left=10, top=20, width=200, height=250)
```
