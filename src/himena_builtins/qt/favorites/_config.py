from himena.plugins import config_field
from dataclasses import dataclass


@dataclass
class FavoriteCommandsConfig:
    """Configuration for the favorite commands widget."""

    commands: list[str] = config_field(
        default_factory=list,
        tooltip="List of favorite commands.",
        widget_type="ListEdit",
        layout="vertical",
        annotation="list[str]",
    )
