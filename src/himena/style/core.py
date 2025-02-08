from __future__ import annotations

from dataclasses import dataclass, asdict
import warnings
from himena.utils.misc import lru_cache
import json
from pathlib import Path
from cmap import Color


@dataclass(frozen=True)
class Theme:
    name: str
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
        color = Color(self.background)
        r, g, b, a = color
        return 0.299 * r + 0.587 * g + 0.114 * b > 0.5


def _mix_colors(x: Color, y: Color, ratio: float) -> Color:
    """Mix two colors."""
    xr, xg, xb, _ = x.rgba
    yr, yg, yb, _ = y.rgba
    return Color(
        [
            xr * (1 - ratio) + yr * ratio,
            xg * (1 - ratio) + yg * ratio,
            xb * (1 - ratio) + yb * ratio,
        ]
    )


@lru_cache(maxsize=1)
def get_global_styles() -> dict[str, Theme]:
    global_styles = {}
    with open(Path(__file__).parent / "defaults.json") as f:
        js: dict = json.load(f)
        for name, style in js.items():
            bg = Color(style["background"])
            fg = Color(style["foreground"])
            base = Color(style["base_color"])
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
            global_styles[name] = Theme(name=name, **style)
    return global_styles


def default_style() -> Theme:
    return get_global_styles()["light-green"]
