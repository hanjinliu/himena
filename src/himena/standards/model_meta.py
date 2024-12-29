from typing import Any, TYPE_CHECKING, Callable, Literal
from pydantic_compat import BaseModel, Field, field_validator
from himena.standards import roi

if TYPE_CHECKING:
    from pydantic import ValidationInfo


class TextMeta(BaseModel):
    """Preset for describing the metadata for a "text" type."""

    language: str | None = Field(None, description="Language of the text file.")
    spaces: int = Field(4, description="Number of spaces for indentation.")
    selection: tuple[int, int] | None = Field(None, description="Selection range.")
    font_family: str | None = Field(None, description="Font family.")
    font_size: float = Field(10, description="Font size.")
    encoding: str | None = Field(None, description="Encoding of the text file.")


class TableMeta(BaseModel):
    """Preset for describing the metadata for a "table" type."""

    current_position: list[int] | None = Field(
        None, description="Current position of (row, columns)."
    )
    selections: list[tuple[tuple[int, int], tuple[int, int]]] = Field(
        default_factory=list,
        description="Selections of the table. Each selection is a pair of slices.",
    )
    separator: str | None = Field(None, description="Separator of the table.")


class DataFrameMeta(TableMeta):
    """Preset for describing the metadata for a "dataframe" type."""


class ExcelMeta(TableMeta):
    """Preset for describing the metadata for a "excel" type."""

    current_sheet: str | None = Field(None, description="Current sheet name.")


class DataFramePlotMeta(DataFrameMeta):
    """Preset for describing the metadata for a "dataframe.plot" type."""

    plot_type: Literal["line", "scatter"] = Field(
        "line", description="Type of the plot."
    )
    plot_color_cycle: Any | None = Field(None, description="Color cycle of the plot.")
    plot_background_color: Any | None = Field(
        "#FFFFFF", description="Background color of the plot."
    )


class ArrayAxis(BaseModel):
    """An axis in an array."""

    name: str = Field(..., description="Name of the axis.")
    scale: float | None = Field(None, description="Pixel scale of the axis.")
    origin: float = Field(0.0, description="Offset of the axis.")
    unit: str | None = Field(None, description="Unit of the axis spacing.")

    @field_validator("name", mode="before")
    def _name_to_str(cls, v):
        return str(v)


class ArrayMeta(BaseModel):
    """Preset for describing an array metadata."""

    axes: list[ArrayAxis] | None = Field(None, description="Axes of the array.")
    current_indices: tuple[Any, ...] | None = Field(
        None, description="Current slice indices to render the array in GUI."
    )
    selections: list[Any] = Field(
        default_factory=list,
        description="Selections of the array. This attribute should be any sliceable "
        "objects that can passed to the backend array object.",
    )
    unit: Any | None = Field(
        None,
        description="Unit of the array values.",
    )

    def without_selections(self) -> "ArrayMeta":
        """Make a copy of the metadata without selections."""
        return self.model_copy(update={"selections": []})


class ImageChannel(BaseModel):
    """A channel in an image file."""

    name: str | None = Field(None, description="Name of the channel.")
    colormap: Any | None = Field(None, description="Color map of the channel.")
    contrast_limits: tuple[float, float] | None = Field(
        None, description="Contrast limits of the channel."
    )
    visible: bool = Field(True, description="Whether the channel is visible.")

    @classmethod
    def default(cls) -> "ImageChannel":
        """Return a default channel (also used for mono-channel images)."""
        return cls(name=None, colormap="gray", contrast_limits=None)

    def with_colormap(self, colormap: Any) -> "ImageChannel":
        """Set the colormap of the channel."""
        return self.model_copy(update={"colormap": colormap})


class ImageMeta(ArrayMeta):
    """Preset for describing an image file metadata."""

    channels: list[ImageChannel] = Field(
        default_factory=lambda: [ImageChannel.default()],
        description="Channels of the image. At least one channel is required.",
    )
    channel_axis: int | None = Field(None, description="Channel axis of the image.")
    is_rgb: bool = Field(False, description="Whether the image is RGB.")
    current_roi: roi.ImageRoi | None = Field(
        None, description="Current region of interest."
    )
    rois: roi.RoiListModel | Callable[[], roi.RoiListModel] = Field(
        default_factory=roi.RoiListModel, description="Regions of interest."
    )
    labels: Any | None = Field(None, description="Labels of the image.")
    interpolation: str | None = Field(None, description="Interpolation method.")
    skip_image_rerendering: bool = Field(
        False,
        description="Skip image rerendering when the model is passed to the "
        "`update_model` method. This field is only used when a function does not touch "
        "the image data itself.",
    )
    more_metadata: Any | None = Field(None, description="More metadata if exists.")

    def without_rois(self) -> "ImageMeta":
        return self.model_copy(update={"rois": roi.RoiListModel(), "current_roi": None})

    def get_one_axis(self, index: int, value: int) -> "ImageMeta":
        """Drop an axis by index."""
        if index < 0:
            index += len(self.axes)
        if index < 0 or index >= len(self.axes):
            raise IndexError(f"Invalid axis index: {index}.")
        axes = self.axes.copy()
        del axes[index]
        update = {"axes": axes}
        caxis = self.channel_axis
        if (caxis := self.channel_axis) == index:
            update["channels"] = [self.channels[value]]
            update["channel_axis"] = None
            update["is_rgb"] = False
        elif caxis is not None:
            update["channel_axis"] = caxis - 1 if caxis > index else caxis
        # TODO: Drop rois for now, but eventually consider them
        return self.model_copy(update=update)

    @field_validator("axes", mode="before")
    def _strings_to_axes(cls, v, values: "ValidationInfo"):
        if v is None:
            return None
        out: list[ArrayAxis] = []
        for axis in v:
            if isinstance(axis, str):
                axis = ArrayAxis(name=axis)
            elif isinstance(axis, dict):
                axis = ArrayAxis(**axis)
            out.append(axis)
        return out

    @field_validator("channel_axis")
    def _is_rgb_and_channels_exclusive(cls, v, values: "ValidationInfo"):
        if values.data.get("is_rgb") and v is not None:
            raise ValueError("Channel axis must be None for RGB images.")
        if v is None and len(values.data["channels"]) > 1:
            raise ValueError("Channel axis is required for multi-channel images.")
        return v

    @field_validator("channels")
    def _channels_not_empty(cls, v, values: "ValidationInfo"):
        if not v:
            raise ValueError("At least one channel is required.")
        return v

    @property
    def contrast_limits(self) -> tuple[float, float] | None:
        """Return the contrast limits of the first visible channel."""
        return self.channels[0].contrast_limits

    @contrast_limits.setter
    def contrast_limits(self, value: tuple[float, float] | None):
        """Set the contrast limits of all channels."""
        for channel in self.channels:
            channel.contrast_limits = value

    @property
    def colormap(self) -> Any | None:
        """Return the colormap of the first visible channel."""
        return self.channels[0].colormap

    @colormap.setter
    def colormap(self, value: Any | None):
        """Set the colormap of all channels."""
        for channel in self.channels:
            channel.colormap = value

    @property
    def current_indices_channel_composite(self) -> tuple[int | slice, ...]:
        """Return the current indices with the channel axis set to slice(None)."""
        if self.current_indices is None:
            raise ValueError("Tried to obtain current indices but it is not set.")
        indices = list(self.current_indices)
        if self.channel_axis is not None:
            indices[self.channel_axis] = slice(None)
        indices = tuple(indices)
        return indices


class ImageRoisMeta(BaseModel):
    """Preset for describing an image-rois metadata."""

    axes: list[ArrayAxis] | None = Field(None, description="Axes of the ROIs.")
    selections: list[int] = Field(default_factory=list)
