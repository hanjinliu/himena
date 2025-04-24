import json
from pathlib import Path
from typing import Any, TYPE_CHECKING, Callable, Literal
import warnings
from pydantic_compat import BaseModel, Field, field_validator
from himena.consts import StandardType
from himena.standards import roi
from himena.standards._base import BaseMetadata, _META_NAME

if TYPE_CHECKING:
    from pydantic import ValidationInfo

__all__ = [
    "TextMeta",
    "TableMeta",
    "DataFrameMeta",
    "DictMeta",
    "FunctionMeta",
    "DataFramePlotMeta",
    "ImageChannel",
    "DimAxis",
    "ArrayMeta",
    "ImageMeta",
    "ImageRoisMeta",
]


class TextMeta(BaseMetadata):
    """Preset for describing the metadata for a "text" type."""

    language: str | None = Field(None, description="Language of the text file.")
    spaces: int = Field(4, description="Number of spaces for indentation.")
    selection: tuple[int, int] | None = Field(None, description="Selection range.")
    font_family: str | None = Field(None, description="Font family.")
    font_size: float = Field(10, description="Font size.")
    encoding: str | None = Field(None, description="Encoding of the text file.")

    def expected_type(self):
        return StandardType.TEXT


class TableMeta(BaseMetadata):
    """Preset for describing the metadata for a "table" type."""

    current_position: list[int] | None = Field(
        default=None,
        description="Current index position of (row, column) in the table.",
    )
    selections: list[tuple[tuple[int, int], tuple[int, int]]] = Field(
        default_factory=list,
        description="Table selections in the format of ((row_start, row_end), (col_start, col_end)), where the end index is exclusive, as is always the case for the Python indexing.",
    )
    separator: str | None = Field(None, description="Separator of the table.")

    def expected_type(self):
        return StandardType.TABLE


class DataFrameMeta(TableMeta):
    """Preset for describing the metadata for a "dataframe" type."""

    transpose: bool = Field(
        default=False, description="Whether the table is transposed."
    )

    def expected_type(self):
        return StandardType.DATAFRAME


class DictMeta(BaseMetadata):
    current_tab: str | None = Field(None, description="Current tab name.")
    child_meta: dict[str, BaseMetadata] = Field(
        default_factory=dict, description="Metadata of the child models."
    )

    def expected_type(self):
        return StandardType.DICT


class FunctionMeta(BaseMetadata):
    """Preset for describing the metadata for a "function" type."""

    source_code: str | None = Field(None, description="Source code of the function.")

    def expected_type(self):
        return StandardType.FUNCTION


class DataFramePlotMeta(DataFrameMeta):
    """Preset for describing the metadata for a "dataframe.plot" type."""

    model_config = {"arbitrary_types_allowed": True}

    plot_type: Literal["line", "scatter"] = Field(
        "line", description="Type of the plot."
    )
    plot_color_cycle: list[str] | None = Field(
        None, description="Color cycle of the plot."
    )
    plot_background_color: str | None = Field(
        "#FFFFFF", description="Background color of the plot."
    )
    rois: roi.RoiListModel | Callable[[], roi.RoiListModel] = Field(
        default_factory=roi.RoiListModel, description="Regions of interest."
    )

    @classmethod
    def from_metadata(cls, dir_path: Path) -> "DataFramePlotMeta":
        self = cls.model_validate_json(dir_path.joinpath(_META_NAME).read_text())
        if (rois_path := dir_path.joinpath("rois.roi.json")).exists():
            self.rois = roi.RoiListModel.model_validate_json(rois_path.read_text())
        return self

    def unwrap_rois(self) -> roi.RoiListModel:
        """Unwrap the lazy-evaluation of the ROIs."""
        if isinstance(self.rois, roi.RoiListModel):
            return self.rois
        self.rois = self.rois()
        return self.rois

    def write_metadata(self, dir_path: Path) -> None:
        dir_path.joinpath(_META_NAME).write_text(self.model_dump_json(exclude={"rois"}))
        rois = self.unwrap_rois()
        if len(rois) > 0:
            dir_path.joinpath("rois.roi.json").write_text(
                json.dumps(rois.model_dump_typed())
            )
        return None

    def expected_type(self):
        return StandardType.DATAFRAME_PLOT


class ImageChannel(BaseModel):
    """A channel in an image file."""

    colormap: str | None = Field(None, description="Color map of the channel.")
    contrast_limits: tuple[float, float] | None = Field(
        None, description="Contrast limits of the channel."
    )
    visible: bool = Field(True, description="Whether the channel is visible.")

    @classmethod
    def default(cls) -> "ImageChannel":
        """Return a default channel (also used for mono-channel images)."""
        return cls(name=None, colormap="gray", contrast_limits=None)

    def with_colormap(self, colormap: str) -> "ImageChannel":
        """Set the colormap of the channel."""
        return self.model_copy(update={"colormap": colormap})


class DimAxis(BaseModel):
    """A dimension axis."""

    name: str = Field(..., description="Name of the axis.")
    scale: float = Field(default=1.0, description="Pixel scale of the axis.")
    origin: float = Field(default=0.0, description="Offset of the axis.")
    unit: str = Field("", description="Unit of the axis spacing.")
    labels: list[str] = Field(
        default_factory=list, description="Category labels of the axis."
    )
    default_label_format: str = Field(
        "{:s}", description="Default format of the labels."
    )

    @field_validator("name", mode="before")
    def _name_to_str(cls, v):
        return str(v)

    @classmethod
    def parse(cls, obj) -> "DimAxis":
        if isinstance(obj, str):
            axis = DimAxis(name=obj)
        elif isinstance(obj, dict):
            axis = DimAxis(**obj)
        elif isinstance(obj, DimAxis):
            axis = obj
        else:
            raise TypeError(f"Cannot convert {type(obj)} to DimAxis.")
        return axis

    def get_label(self, index: int) -> str:
        """Return the label of the axis at the given index."""
        if index < 0:
            raise ValueError("Index must be non-negative.")
        try:
            return self.labels[index]
        except IndexError:
            return self.default_label_format.format(str(index))


def __getattr__(name: str):  # pragma: no cover
    if name == "ArrayAxis":
        warnings.warn(
            "ArrayAxis is deprecated. Use DimAxis instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return DimAxis
    raise AttributeError(f"module {__name__} has no attribute {name}")


class ArrayMeta(BaseMetadata):
    """Preset for describing an array metadata."""

    axes: list[DimAxis] | None = Field(None, description="Axes of the array.")
    current_indices: tuple[int | None, ...] | None = Field(
        None, description="Current slice indices to render the array in GUI."
    )
    selections: list[tuple[tuple[int, int], tuple[int, int]]] = Field(
        default_factory=list,
        description="Selections of the array. This attribute should be any sliceable "
        "objects that can passed to the backend array object.",
    )
    unit: str | None = Field(
        None,
        description="Unit of the array values.",
    )

    def without_selections(self) -> "ArrayMeta":
        """Make a copy of the metadata without selections."""
        return self.model_copy(update={"selections": []})

    def expected_type(self):
        return StandardType.ARRAY


class ImageMeta(ArrayMeta):
    """Preset for describing an image file metadata."""

    model_config = {"arbitrary_types_allowed": True}

    channels: list[ImageChannel] = Field(
        default_factory=lambda: [ImageChannel.default()],
        description="Channels of the image. At least one channel is required.",
    )
    channel_axis: int | None = Field(None, description="Channel axis of the image.")
    is_rgb: bool = Field(False, description="Whether the image is RGB.")
    current_roi: roi.RoiModel | int | None = Field(
        None, description="Current region of interest"
    )
    current_roi_index: int | None = Field(
        None, description="Current index of the ROI in the `rois`, if applicable."
    )
    rois: roi.RoiListModel | Callable[[], roi.RoiListModel] = Field(
        default_factory=roi.RoiListModel, description="Regions of interest."
    )
    interpolation: str | None = Field(
        default=None,
        description="Interpolation method.",
    )
    skip_image_rerendering: bool = Field(
        default=False,
        description="Skip image rerendering when the model is passed to the `update_model` method. This field is only used when a function does not touch the image data itself.",
    )
    more_metadata: Any | None = Field(None, description="More metadata if exists.")

    def without_rois(self) -> "ImageMeta":
        return self.model_copy(update={"rois": roi.RoiListModel(), "current_roi": None})

    def get_one_axis(self, index: int, value: int) -> "ImageMeta":
        """Drop an axis by index for the array slicing arr[..., value, ...]."""
        if index < 0:
            index += len(self.axes)
        if index < 0 or index >= len(self.axes):
            raise IndexError(f"Invalid axis index: {index}.")
        axes = self.axes.copy()
        del axes[index]
        update = {"axes": axes, "rois": self.unwrap_rois().take_axis(index, value)}
        if (caxis := self.channel_axis) == index:
            update["channels"] = [self.channels[value]]
            update["channel_axis"] = None
            update["is_rgb"] = False
        elif caxis is not None:
            update["channel_axis"] = caxis - 1 if caxis > index else caxis
        return self.model_copy(update=update)

    def with_current_roi(self, roi: roi.RoiModel) -> "ImageMeta":
        """Set the current ROI."""
        update = {"current_roi": roi}
        if self.current_roi_index is not None:
            rois = self.unwrap_rois()
            rois.items[self.current_roi_index] = roi
            update["rois"] = rois
        return self.model_copy(update=update)

    def unwrap_rois(self) -> roi.RoiListModel:
        """Unwrap the lazy-evaluation of the ROIs."""
        if isinstance(self.rois, roi.RoiListModel):
            return self.rois
        self.rois = self.rois()
        return self.rois

    @field_validator("axes", mode="before")
    def _strings_to_axes(cls, v):
        if v is None:
            return None
        return [DimAxis.parse(axis) for axis in v]

    @field_validator("channel_axis")
    def _is_rgb_and_channels_exclusive(cls, v, values: "ValidationInfo"):
        if values.data.get("is_rgb") and v is not None:
            raise ValueError("Channel axis must be None for RGB images.")
        if v is None and len(values.data.get("channels", [])) > 1:
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

    @classmethod
    def from_metadata(cls, dir_path: Path) -> "ImageMeta":
        self = cls.model_validate_json(dir_path.joinpath(_META_NAME).read_text())
        if (rois_path := dir_path.joinpath(_ROIS)).exists():
            self.rois = roi.RoiListModel.model_validate_json(rois_path.read_text())
        if (cur_roi_path := dir_path.joinpath(_CURRENT_ROI)).exists():
            roi_js = json.loads(cur_roi_path.read_text())
            self.current_roi = roi.RoiModel.construct(roi_js.pop("type"), roi_js)
        if (more_meta_path := dir_path.joinpath(_MORE_META)).exists():
            with more_meta_path.open() as f:
                self.more_metadata = json.load(f)
        return self

    def write_metadata(self, dir_path: Path) -> None:
        dir_path.joinpath(_META_NAME).write_text(
            self.model_dump_json(
                exclude={"current_roi", "rois", "labels", "more_metadata"}
            )
        )
        rois = self.unwrap_rois()
        if isinstance(cur_roi := self.current_roi, roi.RoiModel):
            dir_path.joinpath(_CURRENT_ROI).write_text(
                json.dumps(cur_roi.model_dump_typed())
            )
        if len(rois) > 0:
            dir_path.joinpath(_ROIS).write_text(json.dumps(rois.model_dump_typed()))
        if (more_metadata := self.more_metadata) is not None:
            try:
                dir_path.joinpath(_MORE_META).write_text(json.dumps(more_metadata))
            except Exception as e:
                warnings.warn(
                    f"Failed to save `more_metadata`: {e}",
                    UserWarning,
                    stacklevel=2,
                )
        return None

    def expected_type(self):
        return StandardType.IMAGE


_CURRENT_ROI = "current_roi.json"
_ROIS = "rois.roi.json"
_MORE_META = "more_meta.json"


class ListMeta(BaseMetadata):
    """Preset for describing a metadata for a list-like object."""

    selections: list[int] = Field(default_factory=list)


class ImageRoisMeta(ListMeta):
    """Preset for describing an image-rois metadata."""

    axes: list[DimAxis] | None = Field(None, description="Axes of the ROIs.")

    def expected_type(self):
        return StandardType.ROIS
