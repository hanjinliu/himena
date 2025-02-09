# Dock Widgets

[Dock widgets](../usage/basics.md#appearance) can be added to the `himena` main window.
Unlike the widgets that are supposed to be added to inside sub-windows, dock widgets
don't need any `WidgetDataModel` to represent their state.

??? note "When to use dock widgets?"

    Unlike sub-windows, dock widgets are always visible to the user but don't have any
    internal data. Therefore, dock widgets are suitable for widgets that make data
    processing routines more efficiently. For example, dock widgets defined in
    `himena_builtins` include:

    - Python interpreter console.
    - File explorers.
    - Command history viewer.

## Register Widget

``` python
from himena.plugin import register_dock_widget_action

class MyDockWidget:
    ...  # implementation

@register_dock_widget_action(
    title="My Dock Widget",  # (1)
    area="bottom",  # (2)
)
def my_dock_widget_action(ui):
    # Construct and return the dock widget.
    return MyDockWidget(ui)
```

1. `title`: The title of the dock widget.
2. `area`: The area where the dock widget is placed. The value can be one of `"left"`,
   `"right"`, `"top"`, or `"bottom"`.

## Plugin Configuration

`himena` natively supports plugin configuration that can be defined by the developer and
customized by the end user in the setting dialog.

To define a plugin configuration, the simplest way is to define a data class.

``` python
from dataclasses import dataclass, field

@dataclass
class MyPluginConfig:
    some_default_value: str = field(default="Hello, world!")
```

Pass the configuration instance to the `register_dock_widget_action` decorator

``` python
@register_dock_widget_action(
    title="My Dock Widget",
    area="bottom",
    config=MyPluginConfig(),
)
def my_dock_widget_action(ui):
    ...
```

and define `update_configs` method in the dock widget class.

``` python
class MyDockWidget:
    def update_configs(self, cfg: MyPluginConfig):
        ... # update the widget state based on the configuration
```

This way, `MyPluginConfig` can be customized in the setting dialog and serialized to the
user profile so that it is persistent across sessions.
