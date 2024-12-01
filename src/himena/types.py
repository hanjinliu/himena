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
    SaveBehavior,
)
from himena._enum import StrEnum
from himena.consts import StandardType

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


class _Void:
    pass


_void = _Void()


class WidgetDataModel(GenericModel[_T]):
    """
    A data model that represents a widget containing an internal data.

    Parameters
    ----------
    value : Any
        Internal value.
    type : str, optional
        Type of the internal data. Type hierarchy is separated by dots. For example,
        "text.plain" is a subtype of "text".
    title : str, optional
        Title for the widget. If not given, the title will be generated from the source
        path when this model is added to the GUI.
    extension_default : str, optional
        Default file extension for saving. This is used when the user saves the data
        without specifying the file extension.
    extensions : list[str], optional
        List of allowed file extensions to save this data.
    metadata : Any, optional
        Metadata that may be used for storing additional information of the internal
        data or describing the state of the widget.
    method : MethodDescriptor, optional
        Method descriptor.
    force_open_with : str, optional
        Force open with a specific plugin if given.
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
    metadata: object | None = Field(
        default=None,
        description="Metadata that may be used for storing additional information of "
        "the internal data or describing the state of the widget.",
    )  # fmt: skip
    method: MethodDescriptor | None = Field(
        default=None,
        description="Method descriptor.",
    )
    force_open_with: str | None = Field(
        default=None,
        description="Force open with a specific plugin if given.",
    )
    save_behavior_override: SaveBehavior | None = Field(
        default=None,
        description="Override the default save behavior.",
    )

    def with_value(
        self,
        value: _U,
        type: str | None = None,
        *,
        title: str | None = None,
        metadata: object | None = _void,
    ) -> "WidgetDataModel[_U]":
        """Return a model with the new value."""
        update = {"value": value}
        if type is not None:
            update["type"] = type
        if metadata is not _void:
            update["metadata"] = metadata
        if title is not None:
            update["title"] = title
        update.update(
            method=None,
            force_open_with=None,
        )  # these parameters must be reset
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
        method: MethodDescriptor | _Void | None = _void,
        save_behavior_override: SaveBehavior | _Void | None = _void,
    ) -> "WidgetDataModel[_T]":
        update = {"force_open_with": open_with}
        if method is not _void:
            update["method"] = method
        if save_behavior_override is not _void:
            update["save_behavior_override"] = save_behavior_override
        return self.model_copy(update=update)

    @property
    def source(self) -> Path | None:
        """The direct source path of the data."""
        if isinstance(self.method, LocalReaderMethod):
            return self.method.path
        return None

    def to_clipboard_data_model(self) -> "ClipboardDataModel":
        """Convert to a clipboard data model."""
        if is_subtype(self.type, StandardType.TEXT):
            return ClipboardDataModel(text=self.value)
        elif is_subtype(self.type, StandardType.HTML):
            return ClipboardDataModel(html=self.value)
        elif is_subtype(self.type, StandardType.IMAGE):
            return ClipboardDataModel(image=self.value)
        raise ValueError(f"Cannot convert {self.type} to a clipboard data.")

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


class ClipboardDataModel(BaseModel):
    """Data model for a clipboard data."""

    text: str | None = Field(
        default=None,
        description="Text in the clipboard if exists.",
    )
    html: str | None = Field(
        default=None,
        description="HTML in the clipboard if exists.",
    )
    image: Any | None = Field(
        default=None,
        description="Image in the clipboard if exists.",
    )
    files: list[Path] = Field(
        default_factory=list,
        description="List of file paths in the clipboard if exists.",
    )


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


class GuiConfiguration(BaseModel):
    """Configuration for parametric widget (interpreted by the injection processor)"""

    title: str | None = None
    preview: bool = False
    auto_close: bool = True
    show_parameter_labels: bool = True


class ModelTrack(BaseModel):
    """Model to track how model is created."""

    sources: list[MethodDescriptor] = Field(default_factory=list)
    command_id: str | None = None

    def to_method(self, parameters: dict[str, Any]) -> MethodDescriptor:
        if self.command_id is not None:
            return ConverterMethod(
                originals=self.sources,
                command_id=self.command_id,
                parameters=parameters,
            )
        return ProgramaticMethod()


class Parametric:
    """Callback for a parametric function.

    This type can be interpreted by the injection store processor. For example, in the
    following code, `my_plugin_function` will be converted into a parametric widget
    with inputs `a` and `b`..

    >>> from himena.plugin import register_function
    >>> @register_function(...)
    >>> def my_plugin_function(...) -> Parametric:
    ...     def callback_func(a: int, b: str) -> WidgetDataModel:
    ...         ...
    ...     return my_plugin_function
    """

    def __new__(cls, *args, **kwargs) -> None:
        if cls is Parametric:
            raise TypeError("Parametric cannot be instantiated.")
        return super().__new__(cls)


class ParametricWidgetProtocol:
    """Protocol used for return annotation of a parametric widget."""

    def __new__(cls, *args, **kwargs) -> None:
        if cls is ParametricWidgetProtocol:
            raise TypeError("ParametricWidgetProtocol cannot be instantiated.")
        return super().__new__(cls)

    def get_output(self, *args, **kwargs) -> Any:
        raise NotImplementedError


class BackendInstructions(BaseModel):
    """Instructions for the backend that are only relevant to user interface."""

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
    choose_one_dialog_response: Callable[[], Any] | None = Field(
        default=None,
        description="If provided, choose-one dialog will be skipped and this function "
        "will be called to get the response.",
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
