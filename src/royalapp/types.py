from pathlib import Path
from typing import (
    Callable,
    Hashable,
    Literal,
    NamedTuple,
    TypeAlias,
    TypeVar,
    Generic,
)
from enum import Enum
from pydantic_compat import BaseModel, Field, validator


class StrEnum(Enum):
    def __repr__(self):
        return f"{self.__class__.__name__}.{self.name}"

    def __str__(self):
        return self.name


class DockArea(Enum):
    """Area of the dock widget."""

    TOP = "top"
    BOTTOM = "bottom"
    LEFT = "left"
    RIGHT = "right"


class SubWindowState(Enum):
    """State of the sub window."""

    MIN = "min"
    MAX = "max"
    NORMAL = "normal"
    FULL = "full"


DockAreaString: TypeAlias = Literal["top", "bottom", "left", "right"]
SubWindowStateString: TypeAlias = Literal["min", "max", "normal", "full"]


class NewWidgetBehavior(Enum):
    """Behavior of adding a widget."""

    TAB = "tab"
    WINDOW = "window"


_T = TypeVar("_T")
_U = TypeVar("_U")


class WidgetDataModel(Generic[_T], BaseModel):
    """A data model that represents a widget containing an internal data."""

    value: _T = Field(..., description="Internal value.")
    source: Path | None = Field(default=None, description="Path of the file.")
    type: Hashable | None = Field(default=None, description="Type of the internal data.")  # fmt: skip
    title: str = Field(default=None, description="Title for the widget.")
    extensions: list[str] = Field(default_factory=list, description="List of allowed file extensions.")  # fmt: skip

    def with_value(
        self, value: _U, type: Hashable | None = None
    ) -> "WidgetDataModel[_U]":
        update = {"value": value}
        if type is not None:
            update["type"] = type
        return self.copy(update=update)

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
        if len(value_repr) > 24:
            value_repr = value_repr[:24] + "..."
        if source := self.source:
            source_repr = source.as_posix()
        else:
            source_repr = None
        return (
            f"{self.__class__.__name__}(value={value_repr}, source={source_repr}), "
            f"type={self.type!r}, title={self.title!r})"
        )


class ClipboardDataModel(Generic[_T], BaseModel):
    """Data model for a clipboard data."""

    value: _T = Field(..., description="Internal value.")
    type: Hashable | None = Field(default=None, description="Type of the internal data.")  # fmt: skip

    def to_widget_data_model(self) -> WidgetDataModel[_T]:
        return WidgetDataModel(value=self.value, type=self.type, title="Clipboard")


class DragDropDataModel(Generic[_T], BaseModel):
    """Data model for a drag and drop data."""

    value: _T = Field(..., description="Internal value.")
    type: Hashable | None = Field(default=None, description="Type of the internal data.")  # fmt: skip
    title: str = Field(default=None, description="Title for the widget.")
    source: Path | None = Field(default=None, description="Path of the file.")
    source_type: str | None = Field(default=None, description="Type of the source.")  # fmt: skip

    def to_widget_data_model(self) -> WidgetDataModel[_T]:
        return WidgetDataModel(value=self.value, type=self.type, source=self.source)


ReaderFunction = Callable[[Path], WidgetDataModel]
WriterFunction = Callable[[WidgetDataModel], None]


class WindowRect(NamedTuple):
    left: int
    top: int
    width: int
    height: int

    @property
    def right(self):
        return self.left + self.width

    @property
    def bottom(self):
        return self.top + self.height

    @classmethod
    def from_numbers(self, left, top, width, height) -> "WindowRect":
        return WindowRect(int(left), int(top), int(width), int(height))
