from dataclasses import dataclass
from typing import Any

from himena.consts import DefaultFontFamily
from himena.plugins import config_field


@dataclass
class MatplotlibCanvasConfigs:
    """Matplotlib canvas configurations."""

    font_size: int = config_field(10, tooltip="Default font size", label="font.size")
    font_family: str = config_field(
        DefaultFontFamily, tooltip="Default font family", label="font.family"
    )
    axes_spines_top: bool = config_field(
        False, tooltip="Show top spine", label="axes.spines.top"
    )
    axes_spines_right: bool = config_field(
        False, tooltip="Show right spine", label="axes.spines.right"
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "font.size": self.font_size,
            "font.family": self.font_family,
            "axes.spines.top": self.axes_spines_top,
            "axes.spines.right": self.axes_spines_right,
        }
