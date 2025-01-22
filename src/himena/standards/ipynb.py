from typing import Literal, Union
from pydantic_compat import BaseModel, Field, field_validator
import numpy as np
from numpy.typing import NDArray

from himena.utils.misc import ansi2html


class IpynbStreamOutput(BaseModel):
    output_type: Literal["stream"] = "stream"
    name: str = Field(default="stdout")
    text: list[str] = Field(default_factory=list)

    def get_text_plain(self) -> str:
        return "".join(self.text)


class IpynbDisplayDataOutput(BaseModel):
    output_type: Literal["display_data"] = "display_data"
    data: dict = Field(default_factory=dict)
    metadata: dict = Field(default_factory=dict)

    def get_text_plain(self) -> str:
        return "\n".join(self.data.get("text/plain", []))

    def get_text_html(self) -> str:
        return "<br>".join(self.data.get("text/html", []))

    def get_image(self) -> NDArray[np.uint8] | None:
        import base64
        from PIL import Image
        import io

        if "image/png" in self.data:
            img_text = self.data["image/png"]
        elif "image/jpeg" in self.data:
            img_text = self.data["image/jpeg"]
        else:
            return None
        png_data = base64.b64decode(img_text, validate=True)
        buf = io.BytesIO(png_data)
        with Image.open(buf) as img:
            arr = np.array(img.convert("RGBA")).copy()
        return arr


class IpynbExecuteResultOutput(IpynbDisplayDataOutput):
    output_type: Literal["execute_result"] = "execute_result"


class IpynbErrorOutput(BaseModel):
    output_type: Literal["error"] = "error"
    ename: str = Field(default="")
    evalue: str = Field(default="")
    traceback: list[str] = Field(default_factory=list)

    def get_html(self) -> str:
        _html = (
            "\n".join(self.traceback)
            .replace(" ", "&nbsp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace("\n", "<br>")
        )
        out = "".join(ansi2html(_html))
        return out


OutputTypes = Union[
    IpynbStreamOutput,
    IpynbDisplayDataOutput,
    IpynbExecuteResultOutput,
    IpynbErrorOutput,
]


class IpynbCell(BaseModel):
    """Model for a single cell in a Jupyter Notebook."""

    cell_type: str = Field(
        default="code",
        description="Type of cell, such as 'code' or 'markdown'",
    )
    metadata: dict = Field(default_factory=dict)
    source: str = Field("")
    outputs: list[OutputTypes] = Field(default_factory=list)

    @field_validator("source", mode="before")
    def _source_to_str(cls, v) -> str:
        if isinstance(v, list):
            return "".join(v)
        return v


class IpynbMetadata(BaseModel):
    kernel_info: dict = Field(default_factory=dict)
    language_info: dict = Field(default_factory=dict)


class IpynbFile(BaseModel):
    metadata: IpynbMetadata = Field(default_factory=IpynbMetadata)
    nbformat: int | None = Field(None)
    nbformat_minor: int | None = Field(None)
    cells: list[IpynbCell] = Field(default_factory=list)

    @property
    def language(self) -> str:
        lang = self.metadata.language_info.get("name")
        if lang is None:
            lang = "python"
        return lang
