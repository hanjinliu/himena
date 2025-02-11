# Reader and Writer Functions

This section tells you how to extend the "Open File(s) ..." and "Save ..." actions so
that it works for any file types you'd like to use in `himena`.

## Reader/Writer Plugins

`himena` uses a [`register_reader_plugin`][himena.plugins.register_reader_plugin] and
[`register_writer_plugin`][himena.plugins.register_writer_plugin] functions to register
functions as reader/writer plugins.

The example below is a simple text file reader plugin.

``` python
from pathlib import Path
from himena.consts import StandardType
from himena.plugins import register_reader_plugin

@register_reader_plugin
def read_text(path: Path):
    text_value = path.read_text()
    return WidgetDataModel(
        value=text_value,
        type=StandardType.TEXT,
        title=path.name,
    )
```

Now `read_text` is a reader plugin object.

``` python
read_text
```

``` title="Output"
<ReaderPlugin read_text>
```

This is not enough. When a path is given, `himena` does not know which reader function
to be used. To let ".txt" match the reader function we have just defined, use the
`define_matcher` method. The matcher function must return `str` of data type if it can
read the file, and `None` otherwise.

``` python
@read_text.define_matcher
def _(path: Path):
    if path.suffix == ".txt":
        return StandardType.TEXT
    return None
```


??? note "Plugin priority"

    You can define the priority of the plugin to be chosen by passing the `priority`
    argument.

    ``` python
    @register_reader_plugin(priority=10)
    def read_text(path: Path):
        ...
    ```

    `priority` is set to `100` by default, and the default providers have `priority=0`,
    which means that if you override the reader/writer for a file type, your provider
    will always be used.

    If `priority` is negative, the plugin will not be used unless users explicitly
    choose your plugin by "Open File With ..." command.


!!! danger "Matcher must be fast"

    The matcher function must not be a time-consuming function. When the application
    tries to open a file, all registered matcher functions are called.

Similarly, you can define a writer plugin.

``` python
from pathlib import Path
from himena.consts import StandardType
from himena.plugins import register_writer_plugin

@register_writer_plugin
def write_text(path: Path, model: WidgetDataModel):
    return path.write_text(model.value)

@write_text.define_matcher
def _(path: Path):
    if path.suffix == ".txt":
        return True
    return False
```

Unlike readers, matcher function returns `True` if the writer can write the file, and
`False` otherwise.
