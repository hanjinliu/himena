# Plugin System

## Defining the Entry Point

To make your module discoverable by `himena`, you need to configure the `pyproject.toml`
file.

For example, if you have a module named `himena_my_plugin` and all the IO functions are
registered in the `io` submodule, you need to add the following configuration to the
`pyproject.toml` file.

``` toml hl_lines="2"
[project.entry-points."himena.plugin"]
"My Plugin IO" = "himena_my_plugin.io"
```

The "My Plugin IO" is the display name of your plugin, and the value "himena_my_plugin.io"
is the import path to the submodule.

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

## Testing Plugins

To locally test your plugin, first install your package to the python environment

```shell
pip install -e .
```

and run the following command to install to a `himena` profile.

```shell
himena <my-profile> --install himena-my-plugin
```

All the submodules listed in the "himena.plugin" entry point will be imported on the
application startup.

!!! note

    Make sure all the files are imported in the `__init__.py` file of the submodule.

### Test using `pytest`

Testing `himena` plugins sometimes causes problems because `himena` application is
initialized multiple times in the same test session.
To avoid this, you can use the `install_plugin()` helper function to ensure that the
plugin is installed only once in the beginning.

```python title="tests/conftest.py"
from himena.testing import install_plugin
import pytest

@pytest.fixture(scope="session", autouse=True)
def init_pytest(request):
    install_plugin("himena-image")
```

## Single-file Plugin

Sometimes you may prefer to create a plugin in a single file. This is useful for such as
daily data analysis, in which you want to define different functions under different
folders.

You can do this by simply installing a python file.

```shell
himena <my-profile> --install path/to/my_plugin.py
```

The installed files will be run as a script on the startup.
