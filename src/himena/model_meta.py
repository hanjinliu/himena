from typing import Any
from pydantic_compat import BaseModel, Field


class TextMeta(BaseModel):
    """Preset for describing a text file metadata."""

    language: str | None = Field(None, description="Language of the text file.")
    spaces: int = Field(4, description="Number of spaces for indentation.")
    selection: tuple[int, int] | None = Field(None, description="Selection range.")
    font_family: str | None = Field(None, description="Font family.")
    font_size: float | None = Field(None, description="Font size.")


class ImageMeta(BaseModel):
    """Preset for describing an image file metadata."""

    axes: list[str] | None = Field(None, description="Axes of the image.")
    scale: list[float] | None = Field(None, description="Scale of the image.")
    origin: list[float] | None = Field(None, description="Origin of the image.")
    colormaps: Any | None = Field(None, description="Color map of the image.")
