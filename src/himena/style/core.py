from __future__ import annotations

from dataclasses import dataclass, asdict
from himena._utils import lru_cache
import json
from pathlib import Path

from cmap import Color


@dataclass(frozen=True)
class Theme:
    background: str
    foreground: str
    base_color: str
    highlight0: str
    highlight1: str
    background0: str
    background1: str
    inv_color: str

    @classmethod
    def from_global(cls, name: str) -> Theme:
        theme = get_global_styles().get(name, None)
        if theme is None:
            raise ValueError(f"Theme {name!r} not found")
        js = asdict(theme)
        self = cls(**js)
        return self

    def format_text(self, text: str) -> str:
        for name, value in asdict(self).items():
            text = text.replace(f"#[{name}]", f"{value}")
        return text


def _mix_colors(a: Color, b: Color, ratio: float) -> Color:
    """Mix two colors."""
    ar, ag, ab, _ = a.rgba
    br, bg, bb, _ = b.rgba
    return Color(
        [
            (ar * (1 - ratio) + br * ratio),
            (ag * (1 - ratio) + bg * ratio),
            (ab * (1 - ratio) + bb * ratio),
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
            if "background0" not in style:
                style["background0"] = _mix_colors(bg, fg, 0.1).hex
            if "background1" not in style:
                style["background1"] = _mix_colors(bg, fg, -0.1).hex
            if "highlight0" not in style:
                style["highlight0"] = _mix_colors(base, bg, 0.6).hex
            if "highlight1" not in style:
                style["highlight1"] = _mix_colors(base, bg, 0.75).hex
            global_styles[name] = Theme(**style)
    return global_styles
