from dataclasses import dataclass, field

from himena.consts import DefaultFontFamily


@dataclass
class MatplotlibCanvasConfigs:
    """Matplotlib canvas configurations."""

    font_size: int = field(default=10)
    font_family: str = field(default=DefaultFontFamily)

    def to_dict(self) -> dict:
        return {
            "font.size": self.font_size,
            "font.family": self.font_family,
        }
