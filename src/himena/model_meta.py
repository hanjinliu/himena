from typing import Any
from pydantic_compat import BaseModel, Field


class TextMeta(BaseModel):
    """Preset for describing a text file metadata."""

    language: str | None = Field(None, description="Language of the text file.")
    spaces: int = Field(4, description="Number of spaces for indentation.")
    selection: tuple[int, int] | None = Field(None, description="Selection range.")
    font_family: str | None = Field(None, description="Font family.")
    font_size: float | None = Field(None, description="Font size.")
    encoding: str | None = Field(None, description="Encoding of the text file.")


class TableMeta(BaseModel):
    """Preset for describing a table file metadata."""

    current_position: list[int] | None = Field(
        None, description="Current position of (row, columns)."
    )
    selections: list[tuple[tuple[int, int], tuple[int, int]]] = Field(
        default_factory=list,
        description="Selections of the table. Each selection is a pair of slices.",
    )


class DataFrameMeta(TableMeta):
    pass


class ExcelMeta(TableMeta):
    """Preset for describing an Excel file metadata."""

    current_sheet: str | None = Field(None, description="Current sheet name.")


class ArrayMeta(BaseModel):
    """Preset for describing an array metadata."""

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
        description="Unit of the array values. This attribute may be a scalar or an "
        "array.",
    )


class Roi(BaseModel):
    """A region of interest (ROI) model."""

    value: Any = Field(..., description="Value of the ROI.")
    type: str = Field(..., description="Type of the ROI.")


class ImageMeta(ArrayMeta):
    """Preset for describing an image file metadata."""

    axes: list[str] | None = Field(None, description="Axes of the image.")
    scale: list[float] | None = Field(None, description="Pixel scale of the image.")
    origin: list[float] | None = Field(None, description="Origin of the image.")
    colormaps: Any | None = Field(None, description="Color map of the image.")
    channel_axis: int | None = Field(None, description="Channel axis of the image.")
    is_rgb: bool = Field(False, description="Whether the image is RGB.")
    current_roi: Roi | None = Field(None, description="Current region of interest.")
    rois: list[Roi] = Field(default_factory=list, description="Regions of interest.")
    labels: Any | None = Field(None, description="Labels of the image.")
    interpolation: str | None = Field(None, description="Interpolation method.")
    contrast_limits: tuple[float, float] | list[tuple[float, float]] | None = Field(
        None, description="Contrast limits of the image, possible for each channel."
    )
