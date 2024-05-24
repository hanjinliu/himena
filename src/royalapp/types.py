from typing import Literal, TypeAlias, NewType
from enum import StrEnum


class DockArea(StrEnum):
    """Area of the dock widget."""
    TOP = "top"
    BOTTOM = "bottom"
    LEFT = "left"
    RIGHT = "right"

DockAreaString: TypeAlias = Literal["top", "bottom", "left", "right"]

class SubWindowState(StrEnum):
    """State of the sub window."""
    MIN = "min"
    MAX = "max"
    NORMAL = "normal"
    FULL = "full"

SubWindowStateString: TypeAlias = Literal["min", "max", "normal", "full"]

TabTitle = NewType("TabTitle", str)
WindowTitle = NewType("WindowTitle", str)
