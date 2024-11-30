# Reader and Writer Functions

This section tells you how to extend the "Open File(s) ..." and "Save ..." actions so
that it works for any file types you'd like to use in `himena`.

## Reader/Writer Providers

`himena` uses reader/writer providers to choose the reader/writer function for the
given file path. A reader/writer provider is a function that return A reader/writer
function based on the file path. For example, following `read_text_provider` function
provides a function to read a text file but does nothing for other file types.

``` python
import pathlib import Path
from himena.consts import StandardType

def read_text_provider(path: Path):
    if path.suffix != ".txt":
        return None
    return read_text

def read_text(path: Path):
    text_value = path.read_text()
    return WidgetDataModel(
        value=text_value,
        type=StandardType.TEXT,
        title=path.name,
    )
```

And the following `write_text_provider` function provides a function to write a text file but does nothing for other file types.

``` python
import pathlib import Path
from himena.consts import StandardType

def write_text_provider(path: Path):
    if path.suffix != ".txt":
        return None
    return write_text

def write_text(path: Path, model: WidgetDataModel):
    path.write_text(model.value)

```

`himena` has many default reader/writer providers for common file types. You can extend
the coverage of file types that `himena` can handle by `register_reader_provider()` and
`register_writer_provider()` functions.

``` python
from himena.plugins import register_reader_provider, register_writer_provider

register_reader_provider(read_text_provider)
register_writer_provider(write_text_provider)
```

!!! note

    Registered providers have `priority` field. It is set to `priority=100` by default,
    and the default providers have `priority=0`, which means that if you override the
    reader/writer for a specific file type, your provider will be used.
