from typing import Any, Literal
from cmap import Color
from pydantic_compat import BaseModel, Field, field_validator
from pydantic import field_serializer
from himena.consts import PYDANTIC_CONFIG_STRICT


class StyledText(BaseModel):
    model_config = PYDANTIC_CONFIG_STRICT

    text: str = Field(..., description="Text content.")
    size: float | None = Field(None, description="Font size.")
    color: Any | None = Field(None, description="Font color.")
    family: str | None = Field(None, description="Font family.")
    bold: bool = Field(False, description="Bold style or not.")
    italic: bool = Field(False, description="Italic style or not.")
    underline: bool = Field(False, description="Underline style or not.")
    alignment: str | None = Field(None, description="Text alignment.")


class BasePlotModel(BaseModel):
    model_config = PYDANTIC_CONFIG_STRICT
    name: str = Field(default="", description="Name of the plot.")

    @classmethod
    def construct(cls, type: str, dict_: dict[str, Any]) -> "BasePlotModel":
        for subclass in BasePlotModel.__subclasses__():
            if subclass.__name__.lower() == type:
                return subclass(**dict_)
        raise ValueError(f"Unknown plot type: {type!r}")

    @field_validator("name", mode="before")
    def _validate_name(cls, name: str) -> str:
        if name is None:
            return ""
        return name

    def model_dump_typed(self) -> dict[str, Any]:
        return {"type": type(self).__name__.lower(), **self.model_dump()}

    def plot_option_dict(self) -> dict[str, Any]:
        """Return the GUI option dict for this plot for editing."""
        return {"name": {"widget_type": "LineEdit", "value": self.name}}


class Axis(BaseModel):
    """Model that represents a plot axis."""

    model_config = PYDANTIC_CONFIG_STRICT

    lim: tuple[float, float] | None = Field(None, description="Axis limits.")
    scale: Literal["linear", "log"] = Field("linear", description="Axis scale.")
    label: str | StyledText | None = Field(None, description="Axis label.")
    ticks: Any | None = Field(None, description="Axis ticks.")
    grid: bool = Field(False, description="Show grid or not.")

    @field_validator("lim", mode="before")
    def _validate_lim(cls, lim) -> tuple[float, float] | None:
        if lim is None:
            return None
        _lim = tuple(lim)
        if len(_lim) != 2:
            raise ValueError(f"Must be a tuple of 2 floats but got: {lim!r}")
        return _lim


class AxesBase(BaseModel):
    """Layout model for an axes."""

    models: list[BasePlotModel] = Field(
        default_factory=list, description="Child plot models."
    )
    title: str | StyledText | None = Field(None, description="Title of the axes.")

    @field_serializer("models")
    def _serialize_models(self, models: list[BasePlotModel]) -> list[dict]:
        return [model.model_dump_typed() for model in models]

    @field_validator("models", mode="before")
    def _validate_models(cls, models: list):
        out = []
        for model in models:
            if isinstance(model, dict):
                model = model.copy()
                model_type = model.pop("type")
                model = BasePlotModel.construct(model_type, model)
            elif not isinstance(model, BasePlotModel):
                raise ValueError(f"Must be a dict or BasePlotModel but got: {model!r}")
            out.append(model)
        return out


class HasColor(BaseModel):
    color: Any | None = Field(None, description="Color property.")

    @property
    def alpha(self) -> float | None:
        """Return the alpha value of the edge color."""
        if self.color is None:
            return None
        return Color(self.color).alpha

    @alpha.setter
    def alpha(self, value: float | None):
        """Set the alpha value of the edge color."""
        if self.color is None:
            return
        color = Color(list(Color(self.color).rgba[:3]) + [value])
        self.color = color
        return


class Face(HasColor):
    """Model for face properties."""

    hatch: Any | None = Field(None, description="Hatch pattern of the face.")


class Edge(HasColor):
    """Model for edge properties."""

    width: float | None = Field(None, description="Width of the edge.")
    style: Any | None = Field(None, description="Style of the edge.")


def parse_edge(kwargs: dict[str, Any]) -> dict:
    color = kwargs.pop("color", kwargs.pop("edge_color", None))
    width = kwargs.pop("width", kwargs.pop("edge_width", None))
    style = kwargs.pop("style", kwargs.pop("edge_style", None))
    name = kwargs.pop("name", None)
    if kwargs:
        raise ValueError(f"Extra keyword arguments: {list(kwargs.keys())!r}")
    edge = Edge(color=color, width=width, style=style)
    return {"edge": edge, "name": name}


def parse_face_edge(kwargs: dict[str, Any]) -> dict:
    color = kwargs.pop("color", kwargs.pop("face_color", None))
    hatch = kwargs.pop("hatch", kwargs.pop("face_hatch", None))
    kwargs = parse_edge(kwargs)
    if kwargs.get("color") is None:
        kwargs["color"] = color
    face = Face(color=color, hatch=hatch)
    return {"face": face, **kwargs}
