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
from pydantic_compat import BaseModel, Field, field_validator
from royalapp._descriptors import MethodDescriptor, LocalReaderMethod


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
    """
    A data model that represents a widget containing an internal data.

    Parameters
    ----------
    value : Any
        Internal value.
    source : Path, optional
        Path of the source file if exists.
    type : Hashable, optional
        Type of the internal data.
    title : str, optional
        Title for the widget.
    extensions : list[str], optional
        List of allowed file extensions to save this data.
    """

    value: _T = Field(..., description="Internal value.")
    method: MethodDescriptor | None = Field(
        default=None,
        description="Method descriptor.",
    )
    type: Hashable | None = Field(
        default=None, description="Type of the internal data."
    )
    title: str | None = Field(
        default=None,
        description="Default title for the widget.",
    )
    extensions: list[str] = Field(
        default_factory=list,
        description="List of allowed file extensions.",
    )
    additional_data: object | None = Field(
        default=None,
        description="Additional data that may be used for specific widgets.",
    )  # fmt: skip

    def with_value(
        self, value: _U, type: Hashable | None = None
    ) -> "WidgetDataModel[_U]":
        update = {"value": value}
        if type is not None:
            update["type"] = type
        return self.model_copy(update=update)

    def with_source(self, source: str | Path) -> "WidgetDataModel[_T]":
        """Return a new instance with the source path."""
        path = Path(source).resolve()
        to_update = {"method": LocalReaderMethod(path=path)}
        if self.title is None:
            to_update.update({"title": source.name})
        return self.model_copy(update=to_update)

    @property
    def source(self) -> Path | None:
        """The direct source path of the data."""
        if isinstance(self.method, LocalReaderMethod):
            return self.method.path
        return None

    @field_validator("type", mode="before")
    def _validate_type(cls, v, values):
        if v is None:
            return type(values["value"])
        return v

    @field_validator("extensions", mode="before")
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
        return WidgetDataModel(value=self.value, type=self.type)


ReaderFunction = Callable[[Path], WidgetDataModel]
WriterFunction = Callable[[WidgetDataModel, Path], None]


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

    def align_left(self, area_size: "tuple[int, int]") -> "WindowRect":
        return WindowRect(0, self.top, self.width, self.height)

    def align_right(self, area_size: "tuple[int, int]") -> "WindowRect":
        w0, _ = area_size
        return WindowRect(w0 - self.width, self.top, self.width, self.height)

    def align_top(self, area_size: "tuple[int, int]") -> "WindowRect":
        return WindowRect(self.left, 0, self.width, self.height)

    def align_bottom(self, area_size: "tuple[int, int]") -> "WindowRect":
        _, h0 = area_size
        return WindowRect(self.left, h0 - self.height, self.width, self.height)

    def align_center(self, area_size: "tuple[int, int]") -> "WindowRect":
        w0, h0 = area_size
        return WindowRect(
            (w0 - self.width) / 2,
            (h0 - self.height) / 2,
            self.width,
            self.height,
        )

    def resize_relative(self, wratio: float, hratio: float) -> "WindowRect":
        if wratio <= 0 or hratio <= 0:
            raise ValueError("Ratios must be positive.")
        return WindowRect(
            self.left,
            self.top,
            round(self.width * wratio),
            round(self.height * hratio),
        )


class Parametric(Callable[..., _T], Generic[_T]):
    """Parametric function that returns a widget data model."""

    def __call__(self, *args, **kwargs) -> WidgetDataModel[_T]:
        raise NotImplementedError("This method must be implemented by subclasses.")


Connection = Callable[[Callable[[WidgetDataModel], None]], None]


class BackendInstructions(NamedTuple):
    """Instructions for the backend."""

    animate: bool = True

    def updated(self, **kwargs) -> "BackendInstructions":
        params = self._asdict()
        params.update(kwargs)
        return BackendInstructions(**params)
