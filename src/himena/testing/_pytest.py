from __future__ import annotations

import importlib
from himena.utils.entries import get_plugin_info


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
    for info in get_plugin_info(module):
        importlib.import_module(info.place)
