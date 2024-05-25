from pathlib import Path
from typing import Any, Hashable, Literal, TypeAlias, NewType, TypeVar, Generic
from enum import StrEnum
from pydantic_compat import BaseModel, Field, validator


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


class NewWidgetBehavior(StrEnum):
    """Behavior of adding a widget."""

    TAB = "tab"
    WINDOW = "window"


_T = TypeVar("_T")


class FileData(BaseModel, Generic[_T]):
    value: _T
    """Internal data of the file."""
    file_type: Hashable | None = Field(default=None)
    """Type of the file, e.g., 'text', 'image', 'table'."""
    file_path: Path | None = Field(default=None)
    """Path of the file."""
    metadata: dict[str, Any] = Field(default_factory=dict)

    @validator("file_path", pre=True)
    def _validate_file_path(cls, v):
        if isinstance(v, str):
            return Path(v)
        return v

    @validator("file_type", pre=True)
    def _validate_file_type(cls, v, values):
        if v is None:
            return type(values["value"])
        return v

    def __repr__(self):
        value_repr = repr(self.value)
        metadata_repr = repr(self.metadata)
        if len(value_repr) > 24:
            value_repr = value_repr[:24] + "..."
        if len(metadata_repr) > 24:
            metadata_repr = metadata_repr[:24] + "..."
        return (
            f"{self.__class__.__name__}(value={value_repr}, "
            f"file_type={self.file_type!r}, file_path={self.file_path.as_posix()!r}), "
            f"metadata={metadata_repr})"
        )


class ClipBoardData(BaseModel, Generic[_T]):
    value: _T
    """Internal data of the clipboard."""
    clip_type: Hashable | None = Field(default=None)
    """Type of the clipboard, e.g., 'text', 'html', 'image'."""

    @validator("clip_type", pre=True)
    def _validate_clip_type(cls, v, values):
        if v is None:
            return type(values["value"])
        return v
