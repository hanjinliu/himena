from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import NamedTuple
import warnings
from himena._utils import lru_cache
import json
from pathlib import Path


@dataclass(frozen=True)
class Theme:
    background: str
    foreground: str
    base_color: str
    foreground_dim: str
    highlight_dim: str
    highlight: str
    highlight_strong: str
    background_dim: str
    background_strong: str
    inv_color: str

    @classmethod
    def from_global(cls, name: str) -> Theme:
        theme = get_global_styles().get(name, None)
        if theme is None:
            warnings.warn(
                f"Theme {name} not found. Using default theme.",
                UserWarning,
                stacklevel=2,
            )
            theme = get_global_styles()["light-purple"]
        js = asdict(theme)
        self = cls(**js)
        return self

    def format_text(self, text: str) -> str:
        for name, value in asdict(self).items():
            text = text.replace(f"#[{name}]", f"{value}")
        return text

    def is_light_background(self) -> bool:
        color = ColorTuple.from_hex(self.background)
        return (color.r + color.g + color.b) / 3 > 127.5


class ColorTuple(NamedTuple):
    r: int
    g: int
    b: int

    @property
    def hex(self) -> str:
        return f"#{self.r:02x}{self.g:02x}{self.b:02x}"

    @classmethod
    def from_hex(cls, hex: str) -> ColorTuple:
        hex = hex.lstrip("#")
        return cls(*(int(hex[i : i + 2], 16) for i in (0, 2, 4)))


def _mix_colors(x: ColorTuple, y: ColorTuple, ratio: float) -> ColorTuple:
    """Mix two colors."""
    return ColorTuple(
        r=int(x.r * (1 - ratio) + y.r * ratio),
        g=int(x.g * (1 - ratio) + y.g * ratio),
        b=int(x.b * (1 - ratio) + y.b * ratio),
    )


@lru_cache(maxsize=1)
def get_global_styles() -> dict[str, Theme]:
    global_styles = {}
    with open(Path(__file__).parent / "defaults.json") as f:
        js: dict = json.load(f)
        for name, style in js.items():
            bg = ColorTuple.from_hex(style["background"])
            fg = ColorTuple.from_hex(style["foreground"])
            base = ColorTuple.from_hex(style["base_color"])
            if "foreground_dim" not in style:
                style["foreground_dim"] = _mix_colors(fg, bg, 0.6).hex
            if "background_dim" not in style:
                style["background_dim"] = _mix_colors(bg, fg, 0.1).hex
            if "background_strong" not in style:
                style["background_strong"] = _mix_colors(bg, fg, -0.1).hex
            if "highlight_dim" not in style:
                style["highlight_dim"] = _mix_colors(base, bg, 0.8).hex
            if "highlight" not in style:
                style["highlight"] = _mix_colors(base, bg, 0.6).hex
            if "highlight_strong" not in style:
                style["highlight_strong"] = _mix_colors(base, bg, 0.4).hex
            global_styles[name] = Theme(**style)
    return global_styles
