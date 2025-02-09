# Plugin System

To make your module discoverable by `himena`, you need to configure the `pyproject.toml`
file.

For example, if you have a module named `himena_my_plugin` and all the IO functions are
registered in the `io` submodule, you need to add the following configuration to the
`pyproject.toml` file.

``` toml hl_lines="2"
[project.entry-points."himena.plugin"]
"My Plugin IO" = "himena_my_plugin.io"
```

The "My Plugin IO" is the display name of your plugin, and the value is the import path
to the submodule.

!!! note

    You don't have to create a new package just for the plugin. This single TOML field
    will allow your package integrated with `himena`.

To improve the customizability of your plugin, your plugin should be well categorized.
For example, IO, widgets, and data processing functions should be separated into
different submodules.

``` toml
[project.entry-points."himena.plugin"]
"My Plugin IO" = "himena_my_plugin.io"
"My Plugin Widgets" = "himena_my_plugin.widgets"
"My Plugin Data Processing" = "himena_my_plugin.processing"
```
