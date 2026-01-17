from dataclasses import field, MISSING
from pathlib import Path
from typing import Any
from platformdirs import user_data_dir


def config_field(
    default=MISSING,
    *,
    default_factory=MISSING,
    tooltip: str | None = None,
    label: str | None = None,
    choices: list[str] | list[tuple[str, Any]] | None = None,
    widget_type: Any | None = None,
    enabled: bool | None = None,
    visible: bool | None = None,
    **kwargs,
):
    """Field used for plugin config dataclass.

    ```python
    @dataclass
    class MyPluginConfig:
        my_field: str = config_field("abc", tooltip="how to use this")
    ```
    """
    metadata = kwargs.copy()
    if tooltip is not None:
        metadata["tooltip"] = tooltip
    if label is not None:
        metadata["label"] = label
    if choices is not None:
        metadata["choices"] = choices
    if enabled is not None:
        metadata["enabled"] = enabled
    if visible is not None:
        metadata["visible"] = visible
    if widget_type is not None:
        metadata["widget_type"] = widget_type

    return field(
        default=default,
        default_factory=default_factory,
        compare=False,
        metadata=metadata,
    )


def plugin_data_dir(plugin_name: str) -> Path:
    """Get the data directory for plugins.

    This is a convenience function that provides a standard location for storing
    plugin-specific data files. The directory structure is up to the plugin developer,
    thus himena application does not recognize any of the contents.
    """
    out = Path(user_data_dir("himena")) / "plugins" / plugin_name
    out.mkdir(parents=True, exist_ok=True)
    return out
