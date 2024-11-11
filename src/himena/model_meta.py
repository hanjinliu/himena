from typing import Any
from pydantic_compat import BaseModel, Field


class TextMeta(BaseModel):
    """Preset for describing a text file metadata."""

    language: str | None = Field(None, description="Language of the text file.")
    spaces: int = Field(4, description="Number of spaces for indentation.")
    selection: tuple[int, int] | None = Field(None, description="Selection range.")
    font_family: str | None = Field(None, description="Font family.")
    font_size: float | None = Field(None, description="Font size.")


class TableMeta(BaseModel):
    """Preset for describing a table file metadata."""

    current_position: list[int] | None = Field(
        None, description="Current position of (row, columns)."
    )
    selections: list[tuple[slice, slice]] = Field(
        default_factory=list,
        description="Selections of the table. Each selection is a pair of slices.",
    )


class ImageMeta(BaseModel):
    """Preset for describing an image file metadata."""

    axes: list[str] | None = Field(None, description="Axes of the image.")
    scale: list[float] | None = Field(None, description="Scale of the image.")
    origin: list[float] | None = Field(None, description="Origin of the image.")
    colormaps: Any | None = Field(None, description="Color map of the image.")
    channel_axis: int | None = Field(None, description="Channel axis of the image.")
    is_rgb: bool = Field(False, description="Whether the image is RGB.")
    current_indices: list[int] | None = Field(
        None, description="Current slice indices to render the image in GUI."
    )
