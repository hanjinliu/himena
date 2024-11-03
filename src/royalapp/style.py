from __future__ import annotations

from dataclasses import dataclass


@dataclass
class LeveledStyle:
    level_1: str
    level_2: str
    level_3: str


@dataclass
class WidgetStyle:
    background: LeveledStyle
    foreground: LeveledStyle
    highlight: LeveledStyle

    @classmethod
    def default(cls) -> WidgetStyle:
        return WidgetStyle(
            background=LeveledStyle("#f0f0f0", "#d3d3d3", "#a6a6a6"),
            foreground=LeveledStyle("#000000", "#303030", "#606060"),
            highlight=LeveledStyle("#c267e1", "#8045c9", "#5b2fa7"),
        )


def get_style(name: str = "default") -> WidgetStyle:  # TODO: Implement more styles
    return WidgetStyle.default()
