from __future__ import annotations

from pathlib import Path
from typing import Iterator
from dataclasses import dataclass
from importlib.metadata import distributions


@dataclass(frozen=True)
class HimenaPluginInfo:
    name: str
    """Plugin name, such as 'My test plugin'."""
    place: str
    """Plugin place, such as 'himena_test_plugin.io'."""
    version: str
    """Plugin version, such as '0.1.0'."""
    distribution: str
    """Distribution name, such as 'himena-test-plugin'."""

    @classmethod
    def from_local_file(cls, path: str) -> HimenaPluginInfo:
        _path = Path(path).resolve()
        return HimenaPluginInfo(
            name=_path.name,
            place=_path.as_posix(),
            version="0.0.0",
            distribution="<local>",
        )

    def is_local_plugin(self) -> bool:
        return self.distribution == "<local>"


ENTRY_POINT_GROUP_NAME = "himena.plugin"


def iter_plugin_info() -> Iterator[HimenaPluginInfo]:
    """Iterate over all the available plugins in the env."""
    for dist in distributions():
        for ep in dist.entry_points:
            if ep.group == ENTRY_POINT_GROUP_NAME:
                yield HimenaPluginInfo(
                    name=ep.name,
                    place=ep.value,
                    version=dist.version,
                    distribution=dist.name,
                )


def is_submodule(string: str, supertype: str) -> bool:
    """Check if a module is a submodule of another module.

    ``` python
    is_submodule("himena_builtins.io", "himena_builtins")  # True
    is_submodule("himena_builtins.io", "himena_builtins.io")  # True
    is_submodule("himena_builtins.io", "himena_test_plugin.io")  # False
    ```
    """
    string_parts = string.split(".")
    supertype_parts = supertype.split(".")
    if len(supertype_parts) > len(string_parts):
        return False
    return string_parts[: len(supertype_parts)] == supertype_parts
