import json
from pathlib import Path
from typing import Any, TYPE_CHECKING, Callable, Literal
import warnings
import numpy as np
from pydantic_compat import BaseModel, Field, field_validator
from himena.standards import roi
from himena.utils.misc import iter_subclasses

if TYPE_CHECKING:
    from pydantic import ValidationInfo

_META_NAME = "meta.json"
_CLASS_JSON = ".class.json"


class BaseMetadata(BaseModel):
    """The base class for a model metadata."""

    @classmethod
    def from_metadata(cls, dir_path: Path) -> "TextMeta":
        return cls.model_validate_json(dir_path.joinpath(_META_NAME).read_text())

    def write_metadata(self, dir_path: Path) -> None:
        dir_path.joinpath(_META_NAME).write_text(self.model_dump_json())

    def _class_info(self) -> dict:
        return {"name": self.__class__.__name__, "module": self.__class__.__module__}


def read_metadata(dir_path: Path) -> BaseMetadata:
    """Read the metadata from a directory."""
    with dir_path.joinpath(_CLASS_JSON).open("r") as f:
        class_js = json.load(f)
    module = class_js["module"]
    name = class_js["name"]
    for sub in iter_subclasses(BaseMetadata):
        if sub.__name__ == name and sub.__module__ == module:
            metadata_class = sub
            break
    else:
        raise ValueError(f"Metadata class {name=}n {module=} not found.")

    return metadata_class.from_metadata(dir_path)


def write_metadata(meta: BaseMetadata, dir_path: Path) -> None:
    """Write the metadata to a directory."""
    meta.write_metadata(dir_path)
    with dir_path.joinpath(_CLASS_JSON).open("w") as f:
        json.dump(meta._class_info(), f)
    return None


class TextMeta(BaseMetadata):
    """Preset for describing the metadata for a "text" type."""

    language: str | None = Field(None, description="Language of the text file.")
    spaces: int = Field(4, description="Number of spaces for indentation.")
    selection: tuple[int, int] | None = Field(None, description="Selection range.")
    font_family: str | None = Field(None, description="Font family.")
    font_size: float = Field(10, description="Font size.")
    encoding: str | None = Field(None, description="Encoding of the text file.")


class TableMeta(BaseMetadata):
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


class FunctionMeta(BaseMetadata):
    """Preset for describing the metadata for a "function" type."""

    source_code: str | None = Field(None, description="Source code of the function.")


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
            with dir_path.joinpath("rois.roi.json").open("w") as f:
                json.dump(rois.model_dump_typed(), f)
        return None


class PhysicalCoordinate(BaseModel):
    type: Literal["physical"] = "physical"
    scale: float | None = Field(None, description="Pixel scale of the axis.")
    origin: float = Field(0.0, description="Offset of the axis.")
    unit: str | None = Field(None, description="Unit of the axis spacing.")


class CategoricalCoordinate(BaseModel):
    type: Literal["categorical"] = "categorical"
    labels: list[str] = Field(..., description="Category labels of the axis.")


class ArrayAxis(BaseModel):
    """An axis in an array."""

    name: str = Field(..., description="Name of the axis.")
    scale: float | None = Field(None, description="Pixel scale of the axis.")
    origin: float = Field(0.0, description="Offset of the axis.")
    unit: str | None = Field(None, description="Unit of the axis spacing.")
    # TODO: should be:
    # coordinate: Union[Physical, Categorical]

    @field_validator("name", mode="before")
    def _name_to_str(cls, v):
        return str(v)


class ArrayMeta(BaseMetadata):
    """Preset for describing an array metadata."""

    axes: list[ArrayAxis] | None = Field(None, description="Axes of the array.")
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


class ImageChannel(BaseModel):
    """A channel in an image file."""

    name: str | None = Field(None, description="Name of the channel.")
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


class ImageMeta(ArrayMeta):
    """Preset for describing an image file metadata."""

    model_config = {"arbitrary_types_allowed": True}

    channels: list[ImageChannel] = Field(
        default_factory=lambda: [ImageChannel.default()],
        description="Channels of the image. At least one channel is required.",
    )
    channel_axis: int | None = Field(None, description="Channel axis of the image.")
    is_rgb: bool = Field(False, description="Whether the image is RGB.")
    current_roi: roi.RoiModel | None = Field(
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

    def unwrap_rois(self) -> roi.RoiListModel:
        """Unwrap the lazy-evaluation of the ROIs."""
        if isinstance(self.rois, roi.RoiListModel):
            return self.rois
        self.rois = self.rois()
        return self.rois

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

    @classmethod
    def from_metadata(cls, dir_path: Path) -> "ImageMeta":
        self = cls.model_validate_json(dir_path.joinpath(_META_NAME).read_text())
        if (rois_path := dir_path.joinpath("rois.roi.json")).exists():
            self.rois = roi.RoiListModel.model_validate_json(rois_path.read_text())
        if (cur_roi_path := dir_path.joinpath("current_roi.json")).exists():
            roi_js = json.loads(cur_roi_path.read_text())
            self.current_roi = roi.RoiModel.construct(roi_js.pop("type"), roi_js)
        if (labels_path := dir_path.joinpath("labels.npy")).exists():
            self.labels = np.load(labels_path, allow_pickle=False)
        if (more_meta_path := dir_path.joinpath("more_meta.json")).exists():
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
        if cur_roi := self.current_roi:
            with dir_path.joinpath("current_roi.json").open("w") as f:
                json.dump(cur_roi.model_dump_typed(), f)
        if len(rois) > 0:
            with dir_path.joinpath("rois.roi.json").open("w") as f:
                json.dump(rois.model_dump_typed(), f)
        if (labels := self.labels) is not None:
            if isinstance(labels, np.ndarray):
                np.savez_compressed(
                    dir_path.joinpath("labels.npy"), labels, allow_pickle=False
                )
            else:
                warnings.warn(
                    f"Unsupported labels type {type(labels)}. Labels are not saved.",
                    UserWarning,
                    stacklevel=2,
                )
        if (more_metadata := self.more_metadata) is not None:
            try:
                with dir_path.joinpath("more_meta.json").open("w") as f:
                    json.dump(more_metadata, f)
            except Exception as e:
                warnings.warn(
                    f"Failed to save `more_metadata`: {e}",
                    UserWarning,
                    stacklevel=2,
                )
        return None


class ImageRoisMeta(BaseMetadata):
    """Preset for describing an image-rois metadata."""

    axes: list[ArrayAxis] | None = Field(None, description="Axes of the ROIs.")
    selections: list[int] = Field(default_factory=list)
