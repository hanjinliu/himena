from pathlib import Path
from typing import (
    Any,
    Callable,
    Hashable,
    Literal,
    TypeAlias,
    NewType,
    TypeVar,
    Generic,
)
from enum import StrEnum
from pydantic_compat import BaseModel, Field, validator


class DockArea(StrEnum):
    """Area of the dock widget."""

    TOP = "top"
    BOTTOM = "bottom"
    LEFT = "left"
    RIGHT = "right"


class SubWindowState(StrEnum):
    """State of the sub window."""

    MIN = "min"
    MAX = "max"
    NORMAL = "normal"
    FULL = "full"


DockAreaString: TypeAlias = Literal["top", "bottom", "left", "right"]
SubWindowStateString: TypeAlias = Literal["min", "max", "normal", "full"]

TabTitle = NewType("TabTitle", str)
WindowTitle = NewType("WindowTitle", str)


class NewWidgetBehavior(StrEnum):
    """Behavior of adding a widget."""

    TAB = "tab"
    WINDOW = "window"


_T = TypeVar("_T")


class WidgetDataModel(Generic[_T], BaseModel):
    """A data model that represents a widget containing an internal data."""

    value: _T = Field(..., description="Internal value.")
    source: Path | None = Field(default=None, description="Path of the file.")
    type: Hashable | None = Field(default=None, description="Type of the internal data.")  # fmt: skip
    title: str = Field(default=None, description="Title for the widget.")
    extensions: list[str] = Field(default_factory=list, description="List of allowed file extensions.")  # fmt: skip
    metadata: dict[str, Any] = Field(default_factory=dict, description="Metadata of the widget.")  # fmt: skip

    @validator("source", pre=True)
    def _validate_file_path(cls, v):
        if isinstance(v, (str, Path)):
            return Path(v)
        elif v is None:
            return None
        raise TypeError(f"Invalid type for `source`: {type(v)}")

    @validator("type", pre=True, always=True)
    def _validate_type(cls, v, values):
        if v is None:
            return type(values["value"])
        return v

    @validator("title", pre=True, always=True)
    def _validate_title(cls, v, values):
        if v is None:
            src = cls._validate_file_path(values["source"])
            if src is None:
                return "Untitled"
            return src.name
        elif not isinstance(v, str):
            raise TypeError(f"Invalid type for `title`: {type(v)}")
        return v

    @validator("extensions", pre=True)
    def _validate_extensions(cls, v):
        if isinstance(v, str):
            v = [v]
        if not all(isinstance(ext, str) for ext in v):
            raise TypeError(f"Invalid type for `extensions`: {type(v)}")
        return [s if s.startswith(".") else f".{s}" for s in v]

    def __repr__(self):
        value_repr = repr(self.value)
        metadata_repr = repr(self.metadata)
        if len(value_repr) > 24:
            value_repr = value_repr[:24] + "..."
        if len(metadata_repr) > 24:
            metadata_repr = metadata_repr[:24] + "..."
        if source := self.source:
            source_repr = source.as_posix()
        else:
            source_repr = None
        return (
            f"{self.__class__.__name__}(value={value_repr}, source={source_repr}), "
            f"type={self.type!r}, title={self.title!r}, metadata={metadata_repr})"
        )


class ClipBoardDataModel(Generic[_T], BaseModel):
    """Data model for a clipboard data."""

    value: _T = Field(..., description="Internal value.")
    type: Hashable | None = Field(default=None, description="Type of the internal data.")  # fmt: skip

    def to_widget_data_model(self) -> WidgetDataModel[_T]:
        return WidgetDataModel(value=self.value, type=self.type, title="Clipboard")


ReaderFunction = Callable[[Path], WidgetDataModel]
WriterFunction = Callable[[WidgetDataModel], None]
