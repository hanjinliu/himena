# Register Functions

To process and analyze data, you need functions that convert an object into another.
This section tells you how to register such functions so that you can run them on the
GUI.

## Function Definition

Basically, a function that processes data is a function that takes a `WidgetDataModel`
object and returns another `WidgetDataModel` object. For example, the following function
formats a non-indented json text data into an indented, pretty json text data.

``` python
from himena import WidgetDataModel

def format_json(model: WidgetDataModel) -> WidgetDataModel:
    value = json.dumps(json.loads(model.value), indent=4)
    return WidgetDataModel(value=value, type="text")
```

Because `himea` has its default widget for `"text"`-type model, this function can be
readly used in the GUI. You can register this function using `register_function()` function.

``` python hl_lines="4"
from himena import WidgetDataModel
from himena.plugins import register_function

@register_function(title="Format JSON Text")
def format_json(model: WidgetDataModel) -> WidgetDataModel:
    value = json.dumps(json.loads(model.value), indent=4)
    return WidgetDataModel(value=value, type="text")
```

The registered function will be shown in the menu bar (under the "Plugins" menu by
default) and the command palette. When this function is called from the GUI, currently
active window will be converted into a `WidgetDataModel` object and passed to the
function. The returned `WidgetDataModel` object will then be converted into another
window.

## Dependency Injection and Type Narrowing

`himena` uses [`in_n_out`](https://github.com/pyapp-kit/in-n-out) library to inject
the application context into functions. For example, in the previous example, the
`WidgetDataModel` of the current window is injected to the `model` argument of the
`format_json` function. If no window is activated, the "Format JSON Text" menu is grayed
out.

A problem of the example above is that the `model` argument may contain any type of
data (not only `"text"`-type data). To narrow the type of data, you can use the `types`
argument of the `register_function()` decorator.

``` python hl_lines="5"
from himena.consts import StandardType

@register_function(
    title="Format JSON Text",
    types=[StandardType.TEXT],
)
def format_json(model: WidgetDataModel) -> WidgetDataModel:
    ...
```

With this, the "Format JSON Text" menu will be enabled only if the current window is a
widget for `"text"`-type data.

## Parametric Functions

Many functions require parameters to work. It is very easy to implement a parametric
function in Python: just add more arguments to the function. However, implementing
a parametric functions in GUI is usually tedious, as you need to create a specific
widget for every function.

`himena` uses [`magicgui`](https://github.com/pyapp-kit/magicgui) library to convert a
function with parameters into a GUI widget based on the type hint of the function.
Therefore, **you can easily register a parametric function just by returning a function**
that takes parameters. To tell `himena` that the returned value should be converted into
a GUI for user input of parameters, you need to **annotate the returned value with the
`Parametric` type**.

``` python hl_lines="2"
from himena.plugins import register_function
from himena.types import Parametric

@register_function(
    title="Format JSON Text",
    types=[StandardType.TEXT],
)
def format_json(model: WidgetDataModel) -> Parametric:
    def run_format_json(indent: int = 4):
        value = json.dumps(json.loads(model.value), indent=indent)
        return WidgetDataModel(value=value, type="text")
    return run_format_json
```



## Specify the Place of Menus
