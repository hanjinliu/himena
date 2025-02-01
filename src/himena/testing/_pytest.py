from __future__ import annotations

import importlib
from himena.utils.entries import iter_plugin_info, is_submodule


def install_plugin(module: str):
    """Convenience function to install a plugin during pytest.

    This function is supposed to be used in a fixture so that a himena plugin will be
    installed to the application during the test session.

    ```python
    ## conftest.py
    import pytest
    from himena.testing import install_plugin

    @pytest.fixture(scope="session", autouse=True)
    def init_pytest(request):
        install_plugin("himena-my-plugin-name")
    ```
    """
    found = False
    for info in iter_plugin_info():
        if info.distribution == module:
            importlib.import_module(info.place)
            found = True
        elif is_submodule(info.place, module):
            importlib.import_module(info.place)
            found = True
    if not found:
        raise ValueError(f"Plugin '{module}' not found.")
