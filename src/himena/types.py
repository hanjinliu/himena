from functools import wraps
from pathlib import Path
from typing import (
    Any,
    Callable,
    Literal,
    NamedTuple,
    TypeAlias,
    TypeVar,
    Generic,
    TYPE_CHECKING,
)
from pydantic_compat import BaseModel, Field, field_validator
from himena._descriptors import (
    MethodDescriptor,
    LocalReaderMethod,
    ConverterMethod,
    ProgramaticMethod,
)
from himena._enum import StrEnum

if TYPE_CHECKING:
    from himena.io import PluginInfo


class DockArea(StrEnum):
    """Area of the dock widget."""

    TOP = "top"
    BOTTOM = "bottom"
    LEFT = "left"
    RIGHT = "right"


class WindowState(StrEnum):
    """State of the sub window."""

    MIN = "min"
    MAX = "max"
    NORMAL = "normal"
    FULL = "full"


DockAreaString: TypeAlias = Literal["top", "bottom", "left", "right"]
WindowStateString: TypeAlias = Literal["min", "max", "normal", "full"]


class NewWidgetBehavior(StrEnum):
    """Behavior of adding a widget."""

    TAB = "tab"
    WINDOW = "window"


_T = TypeVar("_T")
_U = TypeVar("_U")

if TYPE_CHECKING:

    class GenericModel(Generic[_T], BaseModel):
        pass
else:

    class GenericModel(BaseModel):
        def __class_getitem__(cls, item):
            return cls


class WidgetDataModel(GenericModel[_T]):
    """
    A data model that represents a widget containing an internal data.

    Parameters
    ----------
    value : Any
        Internal value.
    source : Path, optional
        Path of the source file if exists.
    type : str, optional
        Type of the internal data. Type hierarchy is separated by dots. For example,
        "text.plain" is a subtype of "text".
    title : str, optional
        Title for the widget.
    extensions : list[str], optional
        List of allowed file extensions to save this data.
    """

    value: _T = Field(..., description="Internal value.")
    type: str = Field(..., description="Type of the internal data.")
    title: str | None = Field(
        default=None,
        description="Default title for the widget.",
    )
    extension_default: str | None = Field(
        default=None,
        description="Default file extension for saving.",
    )
    extensions: list[str] = Field(
        default_factory=list,
        description="List of allowed file extensions.",
    )
    additional_data: object | None = Field(
        default=None,
        description="Additional data that may be used for specific widgets.",
    )  # fmt: skip
    method: MethodDescriptor | None = Field(
        default=None,
        description="Method descriptor.",
    )
    force_open_with: str | None = Field(
        default=None,
        description="Force open with a specific plugin if given.",
    )

    def with_value(
        self,
        value: _U,
    ) -> "WidgetDataModel[_U]":
        update = {"value": value}
        return self.model_copy(update=update)

    def _with_source(
        self,
        source: str | Path,
        plugin: "PluginInfo | None" = None,
    ) -> "WidgetDataModel[_T]":
        """Return a new instance with the source path."""
        path = Path(source).resolve()
        if plugin is None:
            plugin_name = None
        else:
            plugin_name = plugin.to_str()
        to_update = {"method": LocalReaderMethod(path=path, plugin=plugin_name)}
        if self.title is None:
            to_update.update({"title": source.name})
        return self.model_copy(update=to_update)

    def with_open_plugin(
        self,
        open_with: str,
        *,
        method: MethodDescriptor | None = None,
    ) -> "WidgetDataModel[_T]":
        update = {"force_open_with": open_with}
        if method is not None:
            update["method"] = method
        return self.model_copy(update=update)

    @property
    def source(self) -> Path | None:
        """The direct source path of the data."""
        if isinstance(self.method, LocalReaderMethod):
            return self.method.path
        return None

    def to_clipboard_data_model(self) -> "ClipboardDataModel[_T]":
        """Convert to a clipboard data model."""
        return ClipboardDataModel(value=self.value, type=self.type)

    def is_subtype_of(self, supertype: str) -> bool:
        """Check if the type is a subtype of the given type."""
        return is_subtype(self.type, supertype)

    @field_validator("type", mode="before")
    def _validate_type(cls, v, values):
        if v is None:
            return type(values["value"])
        return v

    @field_validator("extension_default", mode="after")
    def _validate_extension_default(cls, v: str, values):
        if not v.startswith("."):
            return f".{v}"
        return v

    @field_validator("extensions", mode="before")
    def _validate_extensions(cls, v):
        if isinstance(v, str):
            v = [v]
        if not all(isinstance(ext, str) for ext in v):
            raise TypeError(f"Invalid type for `extensions`: {type(v)}")
        return [s if s.startswith(".") else f".{s}" for s in v]

    def __repr__(self):
        value_repr = f"<{type(self.value).__name__}>"
        if source := self.source:
            source_repr = source.as_posix()
        else:
            source_repr = None
        return (
            f"{self.__class__.__name__}(value={value_repr}, source={source_repr}), "
            f"type={self.type!r}, title={self.title!r})"
        )


class ClipboardDataModel(GenericModel[_T]):
    """Data model for a clipboard data."""

    value: _T = Field(..., description="Internal value.")
    type: str | None = Field(default=None, description="Type of the internal data.")

    def to_widget_data_model(self) -> WidgetDataModel[_T]:
        return WidgetDataModel(value=self.value, type=self.type, title="Clipboard")

    def is_subtype_of(self, supertype: str) -> bool:
        """Check if the type is a subtype of the given type."""
        return is_subtype(self.type, supertype)


class DragDropDataModel(GenericModel[_T]):
    """Data model for a drag and drop data."""

    value: _T = Field(..., description="Internal value.")
    type: str | None = Field(default=None, description="Type of the internal data.")
    title: str = Field(default=None, description="Title for the widget.")
    source: Path | None = Field(default=None, description="Path of the file.")
    source_type: str | None = Field(default=None, description="Type of the source.")

    def to_widget_data_model(self) -> WidgetDataModel[_T]:
        return WidgetDataModel(value=self.value, type=self.type)


def is_subtype(string: str, supertype: str) -> bool:
    """Check if the type is a subtype of the given type.

    >>> is_subtype_of("text", "text")  # True
    >>> is_subtype_of("text.plain", "text")  # True
    >>> is_subtype_of("text.plain", "text.html")  # False
    """
    string_parts = string.split(".")
    supertype_parts = supertype.split(".")
    if len(supertype_parts) > len(string_parts):
        return False
    return string_parts[: len(supertype_parts)] == supertype_parts


ReaderFunction = Callable[[Path], WidgetDataModel]
WriterFunction = Callable[[WidgetDataModel, Path], None]
ReaderProvider = Callable[["Path | list[Path]"], ReaderFunction]
WriterProvider = Callable[[WidgetDataModel], WriterFunction]


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


class Parametric(Generic[_T]):
    """Parametric function that returns a widget data model."""

    def __init__(
        self,
        func: Callable[..., WidgetDataModel[_T]],
        *,
        auto_close: bool = True,
        sources: list[MethodDescriptor] = [],
        action_id: str | None = None,
        preview: bool = False,
    ):
        if isinstance(func, Parametric):
            if len(sources) > 0 or action_id is not None:
                raise TypeError(
                    "The first argument must not be a Parametric if sources are given."
                )
            self._func = func._func
            sources = func.sources
            action_id = func.action_id
        else:
            self._func = func
        wraps(func)(self)
        self._auto_close = auto_close
        self._preview = preview
        self._sources = list(sources)
        self._action_id = action_id

    def __call__(self, *args, **kwargs) -> WidgetDataModel[_T]:
        return self._func(*args, **kwargs)

    @property
    def name(self) -> str:
        if hasattr(self._func, "__name__"):
            return self._func.__name__
        return str(self._func)

    @property
    def sources(self) -> list[MethodDescriptor]:
        return self._sources

    @property
    def action_id(self) -> str | None:
        return self._action_id

    @property
    def preview(self) -> bool:
        """Whether preview is enabled."""
        return self._preview

    def to_method(self, parameters: dict[str, Any]) -> MethodDescriptor:
        if src := self.sources:
            return ConverterMethod(
                originals=src, action_id=self.action_id, parameters=parameters
            )
        return ProgramaticMethod()


class ParametricWidgetTuple(NamedTuple):
    """Used for a return annotation to add a custom parametric widget."""

    widget: Any
    callback: Callable[..., Any]
    title: str | None = None


class BackendInstructions(BaseModel):
    """Instructions for the backend."""

    animate: bool = Field(
        default=True,
        description="Whether to animate",
        frozen=True,
    )
    confirm: bool = Field(
        default=True,
        description="Whether to show a confirmation dialog",
        frozen=True,
    )
    file_dialog_response: Callable[[], Any] | None = Field(
        default=None,
        description="If provided, file dialog will be skipped and this function will "
        "be called to get the response.",
        frozen=True,
    )

    def updated(self, **kwargs) -> "BackendInstructions":
        return self.model_copy(update=kwargs)
