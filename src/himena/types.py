from dataclasses import asdict, dataclass, field
import math
from pathlib import Path
import timeit
from typing import (
    Any,
    Callable,
    ClassVar,
    Literal,
    NamedTuple,
    NewType,
    TypeAlias,
    TypeVar,
    Generic,
    TYPE_CHECKING,
)
from pydantic_compat import BaseModel, Field, field_validator
from himena._descriptors import SaveBehavior
from himena.workflow import (
    Workflow,
    LocalReaderMethod,
    CommandExecution,
    parse_parameter,
)
from himena.utils.enum import StrEnum
from himena.utils.misc import is_subtype
from himena.consts import PYDANTIC_CONFIG_STRICT

if TYPE_CHECKING:
    from typing import Self
    from himena.utils.misc import PluginInfo


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
    workflow : WorkflowList, optional
        History of how this data is created.
    force_open_with : str, optional
        Force open with a specific plugin if given.
    """

    model_config = PYDANTIC_CONFIG_STRICT

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
    workflow: Workflow = Field(default_factory=Workflow)
    force_open_with: str | None = Field(
        default=None,
        description="Force open with a specific plugin if given.",
    )
    save_behavior_override: SaveBehavior | None = Field(
        default=None,
        description="Override the default save behavior.",
    )
    editable: bool = Field(True, description="Whether the widget is editable.")
    window_rect_override: Callable[["Size"], "WindowRect"] | None = Field(None)

    def with_value(
        self,
        value: _U,
        type: str | None = None,
        *,
        title: str | None = None,
        metadata: object | None = _void,
        save_behavior_override: SaveBehavior | _Void | None = _void,
    ) -> "WidgetDataModel[_U]":
        """Return a model with the new value."""
        update = {"value": value}
        if type is not None:
            update["type"] = type
        if metadata is not _void:
            update["metadata"] = metadata
        if title is not None:
            update["title"] = title
        if save_behavior_override is not _void:
            update["save_behavior_override"] = save_behavior_override
        update.update(
            workflow=Workflow(),
            force_open_with=None,
        )  # these parameters must be reset
        return self.model_copy(update=update)

    def astype(self, new_type: str):
        update = {"type": new_type}
        return self.model_copy(update=update)

    def _with_source(
        self,
        source: str | Path | list[str | Path],
        plugin: "PluginInfo | None" = None,
    ) -> "WidgetDataModel[_T]":
        """Return a new instance with the source path."""
        if plugin is None:
            plugin_name = None
        else:
            plugin_name = plugin.to_str()
        if isinstance(source, list):
            path = [Path(s).resolve() for s in source]
        else:
            path = Path(source).resolve()
        wf = LocalReaderMethod(
            path=path, plugin=plugin_name, output_model_type=self.type
        ).construct_workflow()
        to_update = {"workflow": wf}
        if self.title is None:
            if isinstance(path, list):
                to_update.update({"title": "File group"})
            else:
                to_update.update({"title": path.name})
        return self.model_copy(update=to_update)

    def with_open_plugin(
        self,
        open_with: str,
        *,
        workflow: Workflow | _Void | None = _void,
        save_behavior_override: SaveBehavior | _Void | None = _void,
    ) -> "WidgetDataModel[_T]":
        update = {"force_open_with": open_with}
        if workflow is not _void:
            update["workflow"] = workflow
        if save_behavior_override is not _void:
            update["save_behavior_override"] = save_behavior_override
        return self.model_copy(update=update)

    def with_metadata(
        self,
        metadata: Any,
    ) -> "WidgetDataModel[_T]":
        """Return a new instance with the given metadata."""
        update = {"metadata": metadata}
        return self.model_copy(update=update)

    def write_to_directory(
        self,
        directory: str | Path,
        *,
        plugin: str | None = None,
    ) -> Path:
        from himena import _providers

        ins = _providers.WriterProviderStore.instance()
        title = self.title or "Untitled"
        path = Path(directory) / title
        if path.suffix == "":
            if ext := self.extension_default:
                path = path.with_suffix(ext)
            elif exts := self.extensions:
                path = path.with_suffix(exts[0])
            else:
                raise ValueError("Could not determine the file extension.")
        ins.run(self, path, min_priority=0, plugin=plugin)
        return path

    @property
    def source(self) -> Path | list[Path] | None:
        """The direct source path of the data."""
        if isinstance(step := self.workflow.last(), LocalReaderMethod):
            return step.path
        return None

    def is_subtype_of(self, supertype: str) -> bool:
        """Check if the type is a subtype of the given type."""
        return is_subtype(self.type, supertype)

    def with_title_numbering(self, copy: bool = False) -> "WidgetDataModel[_T]":
        """Add [n] suffix to the title."""
        title = self.title
        if title is None:
            title = "Untitled"
        if "." in title:
            stem, ext = title.rsplit(".", 1)
            ext = f".{ext}"
        else:
            stem = title
            ext = ""
        if (
            (last_part := stem.rsplit(" ", 1)[-1]).startswith("[")
            and last_part.endswith("]")
            and last_part[1:-1].isdigit()
        ):
            nth = int(last_part[1:-1])
            stem = stem.rsplit(" ", 1)[0] + f" [{nth + 1}]"
        else:
            stem = stem + " [1]"
        new_title = stem + ext
        if copy:
            return self.model_copy(update={"title": new_title})
        else:
            self.title = new_title
            return self

    @field_validator("extension_default", mode="after")
    def _validate_extension_default(cls, v: str, values):
        if v is None:
            return None
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
        if isinstance(source := self.source, Path):
            source_repr = source.as_posix()
        elif isinstance(source, list):
            if len(source) > 0:
                source_repr = f"[{source[0].as_posix()}, ...]"
            else:
                source_repr = "[]"
        else:
            source_repr = None
        return (
            f"{self.__class__.__name__}(value={value_repr}, source={source_repr}), "
            f"type={self.type!r}, title={self.title!r})"
        )


class ClipboardDataModel(BaseModel):
    """Data model for a clipboard data."""

    model_config = PYDANTIC_CONFIG_STRICT

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


class DragDataModel(BaseModel):
    model_config = PYDANTIC_CONFIG_STRICT
    getter: Callable[[], WidgetDataModel] | WidgetDataModel = Field(
        ..., description="Getter function to get the data model."
    )
    type: str | None = Field(None, description="Type of the internal data.")

    def inferred_type(self) -> str:
        if self.type is not None:
            return self.type
        if callable(self.getter):
            model = self.getter()
        else:
            model = self.getter
        return model.type

    def data_model(self) -> WidgetDataModel:
        if isinstance(self.getter, WidgetDataModel):
            model = self.getter
        else:
            model = self.getter()
        return model

    def widget_accepts_me(self, widget: Any) -> bool:
        """Return true if the widget accepts this data model to be dropped."""
        if hasattr(widget, "allowed_drop_types"):
            types = widget.allowed_drop_types()
            if self.type is None:
                return True  # not specified. Just allow it.
            if self.type in types:
                return True
        elif hasattr(widget, "dropped_callback"):
            return True
        return False


_V = TypeVar("_V", int, float)


@dataclass(frozen=True)
class Size(Generic[_V]):
    """Size use for any place."""

    width: _V
    height: _V

    def __iter__(self):
        """Iterate over the field to make this class tuple-like."""
        return iter((self.width, self.height))

    def __getitem__(self, index: int):
        if index == 0:
            return self.width
        elif index == 1:
            return self.height
        raise IndexError(f"Index {index!r} out of range.")

    def with_width(self, width: _V) -> "Size[_V]":
        return Size(width, self.height)

    def with_height(self, height: _V) -> "Size[_V]":
        return Size(self.width, height)


@dataclass(frozen=True)
class Rect(Generic[_V]):
    """Rectangle use for any place."""

    left: _V
    top: _V
    width: _V
    height: _V

    @property
    def right(self):
        return self.left + self.width

    @property
    def bottom(self):
        return self.top + self.height

    def with_left(self, left: _V) -> "Rect[_V]":
        return Rect(left, self.top, self.width, self.height)

    def with_top(self, top: _V) -> "Rect[_V]":
        return Rect(self.left, top, self.width, self.height)

    def with_width(self, width: _V) -> "Rect[_V]":
        return Rect(self.left, self.top, width, self.height)

    def with_height(self, height: _V) -> "Rect[_V]":
        return Rect(self.left, self.top, self.width, height)

    def with_right(self, right: _V) -> "Rect[_V]":
        return Rect(right - self.width, self.top, self.width, self.height)

    def with_bottom(self, bottom: _V) -> "Rect[_V]":
        return Rect(self.left, bottom - self.height, self.width, self.height)

    def __iter__(self):
        """Iterate over the field to make this class tuple-like."""
        return iter((self.left, self.top, self.width, self.height))

    def size(self) -> Size[_V]:
        return Size(self.width, self.height)

    def adjust_to_int(
        self,
        how: Literal["inner", "outer"] = "inner",
    ) -> "Rect[int]":
        right = self.right
        bottom = self.bottom
        if how == "inner":
            left = int(math.ceil(self.left))
            top = int(math.ceil(self.top))
            right = int(math.floor(right))
            bottom = int(math.floor(bottom))
        else:
            left = int(math.floor(self.left))
            top = int(math.floor(self.top))
            right = int(math.ceil(right))
            bottom = int(math.ceil(bottom))
        return Rect(left, top, right - left, bottom - top)

    def limit_to(self, xmax: _T, ymax: _T) -> "Rect[_T]":
        """Limit the size of the Rect to the given maximum size."""
        left = max(self.left, 0)
        top = max(self.top, 0)
        right = min(self.right, xmax)
        bottom = min(self.bottom, ymax)
        return Rect(left, top, right - left, bottom - top)

    def move_top_left(self, left: _V, top: _V) -> "Rect[_V]":
        return Rect(left, top, self.width, self.height)

    def move_top_right(self, right: _V, top: _V) -> "Rect[_V]":
        return Rect(right - self.width, top, self.width, self.height)

    def move_bottom_left(self, left: _V, bottom: _V) -> "Rect[_V]":
        return Rect(left, bottom - self.height, self.width, self.height)

    def move_bottom_right(self, right: _V, bottom: _V) -> "Rect[_V]":
        return Rect(right - self.width, bottom - self.height, self.width, self.height)


@dataclass(frozen=True)
class WindowRect(Rect[int]):
    """Rectangle of a window."""

    @classmethod
    def from_tuple(cls, left, top, width, height) -> "WindowRect":
        return cls(int(left), int(top), int(width), int(height))

    def align_left(self, area_size: Size[int]) -> "WindowRect":
        return WindowRect(0, self.top, self.width, self.height)

    def align_right(self, area_size: Size[int]) -> "WindowRect":
        w0, _ = area_size
        return WindowRect(w0 - self.width, self.top, self.width, self.height)

    def align_top(self, area_size: Size[int]) -> "WindowRect":
        return WindowRect(self.left, 0, self.width, self.height)

    def align_bottom(self, area_size: Size[int]) -> "WindowRect":
        _, h0 = area_size
        return WindowRect(self.left, h0 - self.height, self.width, self.height)

    def align_center(self, area_size: Size[int]) -> "WindowRect":
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


@dataclass(frozen=True)
class Margins(Generic[_V]):
    left: _V
    top: _V
    right: _V
    bottom: _V

    def __iter__(self):
        """Iterate over the field to make this class tuple-like."""
        return iter((self.left, self.top, self.right, self.bottom))


class _HasDynamicAttribute:
    _ATTR_NAME: str

    @classmethod
    def get(cls, obj) -> "Self | None":
        return getattr(obj, cls._ATTR_NAME, None)

    def set(self, obj) -> None:
        setattr(obj, self._ATTR_NAME, self)


@dataclass
class GuiConfiguration(_HasDynamicAttribute):
    """Configuration for parametric widget (interpreted by the injection processor)"""

    _ATTR_NAME: ClassVar[str] = "__himena_gui_config__"

    title: str | None = None
    preview: bool = False
    auto_close: bool = True
    show_parameter_labels: bool = True
    run_async: bool = False
    result_as: Literal["window", "below", "right"] = "window"
    run_immediately_with: Callable[[], dict[str, Any]] | None = None

    def asdict(self) -> dict[str, Any]:
        """Return the configuration as a dictionary."""
        return asdict(self)


@dataclass(frozen=True)
class ModelTrack(_HasDynamicAttribute):
    """Model to track how model is created."""

    _ATTR_NAME: ClassVar[str] = "__himena_model_track__"

    command_id: str
    contexts: list = field(default_factory=list)
    workflow: Workflow = field(default_factory=Workflow)
    time_start: float = field(default=0.0)

    def to_workflow(self, parameters: dict[str, Any]) -> Workflow:
        params = []
        more_workflows: list[Workflow] = []
        for k, v in parameters.items():
            if k == "is_previewing":
                continue
            param, wf = parse_parameter(k, v)
            params.append(param)
            more_workflows.append(wf)
        workflow = Workflow.concat([self.workflow] + more_workflows)
        return workflow.with_step(
            CommandExecution(
                command_id=self.command_id,
                contexts=self.contexts,
                parameters=params,
                execution_time=timeit.default_timer() - self.time_start,
            )
        )


@dataclass(frozen=True)
class FutureInfo(_HasDynamicAttribute):
    _ATTR_NAME: ClassVar[str] = "__himena_future_info__"

    type_hint: Any
    track: ModelTrack | None = None
    kwargs: dict[str, Any] = field(default_factory=dict)
    top_left: tuple[int, int] | None = None
    size: Size[int] | None = None

    def resolve_type_hint(self, ns: dict[str, Any]) -> "FutureInfo":
        if isinstance(self.type_hint, str):
            typ = ns.get(self.type_hint)
            if typ is None:
                raise ValueError(f"Could not resolve the type hint: {self.type_hint}")
            self.type_hint = typ
        return self


Parametric = NewType("Parametric", Any)
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

    model_config = PYDANTIC_CONFIG_STRICT

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
    gui_execution: bool = Field(default=True)
    process_model_output: bool = Field(default=True)
    unwrap_future: bool = Field(default=False)

    def updated(self, **kwargs) -> "BackendInstructions":
        return self.model_copy(update=kwargs)


class WidgetClassTuple(NamedTuple):
    """Class for storing registered widget class."""

    type: str
    widget_class: "type | Callable"  # factory function
    priority: int = 100
    widget_id: str | None = None


WidgetType = NewType("WidgetType", object)
"""This type is used for the return annotation.

>>> from himena.plugin import register_function
>>> @register_function(...)
>>> def my_plugin_function() -> WidgetType:
...     return MyWidget()
"""

WidgetConstructor = NewType("WidgetConstructor", object)
"""This type is used for the return annotation.

>>> from himena.plugin import register_function
>>> @register_function(...)
>>> def my_plugin_function() -> WidgetConstructor:
...     return MyWidget
"""


class DropResult(BaseModel):
    """Model that can be returned by `dropped_callback` protocol.

    Parameters
    ----------
    delete_input : bool
        Whether to delete the input data if drop succeeded.
    outputs : WidgetDataModel | list[WidgetDataModel] | None
        If given, the output data will be added to the GUI.
    """

    delete_input: bool = False
    outputs: WidgetDataModel | list[WidgetDataModel] | None = Field(None)
