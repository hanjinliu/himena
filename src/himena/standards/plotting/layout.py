from typing import Any, Literal, Sequence, TYPE_CHECKING, SupportsIndex

import numpy as np
from pydantic_compat import BaseModel, Field
from pydantic import field_serializer, field_validator
from himena.standards.plotting import models as _m

if TYPE_CHECKING:
    from typing import Self
    from numpy.typing import NDArray


class BaseLayoutModel(BaseModel):
    hpad: float | None = Field(None, description="Horizontal padding.")
    vpad: float | None = Field(None, description="Vertical padding.")
    hspace: float | None = Field(None, description="Horizontal space.")
    vspace: float | None = Field(None, description="Vertical space.")

    def merge_with(self, other: "BaseLayoutModel") -> "BaseLayoutModel":
        raise NotImplementedError

    def model_dump_typed(self) -> dict:
        return {"type": type(self).__name__.lower(), **self.model_dump()}

    @classmethod
    def construct(self, model_type: str, dict_: dict) -> "BaseLayoutModel":
        if model_type == "singleaxes":
            return SingleAxes.model_validate(dict_)
        if model_type == "row":
            return Row.model_validate(dict_)
        if model_type == "column":
            return Column.model_validate(dict_)
        if model_type == "grid":
            return Grid.model_validate(dict_)
        raise ValueError(f"Unknown layout model type: {model_type!r}")


class StyledText(BaseModel):
    text: str = Field(..., description="Text content.")
    size: float | None = Field(None, description="Font size.")
    color: Any | None = Field(None, description="Font color.")
    family: str | None = Field(None, description="Font family.")
    bold: bool = Field(False, description="Bold style or not.")
    italic: bool = Field(False, description="Italic style or not.")
    underline: bool = Field(False, description="Underline style or not.")
    alignment: str | None = Field(None, description="Text alignment.")


class Axis(BaseModel):
    lim: tuple[float, float] | None = Field(None, description="Axis limits.")
    scale: Literal["linear", "log"] = Field("linear", description="Axis scale.")
    label: str | StyledText | None = Field(None, description="Axis label.")
    ticks: Any | None = Field(None, description="Axis ticks.")
    grid: bool = Field(False, description="Show grid or not.")


class Axes(BaseModel):
    """Layout model for axes."""

    models: list[_m.BasePlotModel] = Field(
        default_factory=list, description="Child plot models."
    )
    title: str | StyledText | None = Field(None, description="Title of the axes.")
    x: Axis = Field(default_factory=Axis, description="X-axis settings.")
    y: Axis = Field(default_factory=Axis, description="Y-axis settings.")

    @field_serializer("models")
    def _serialize_models(self, models: list[_m.BasePlotModel]) -> list[dict]:
        return [model.model_dump_typed() for model in models]

    @field_validator("models", mode="before")
    def _validate_models(cls, models: list) -> list[_m.BasePlotModel]:
        out = []
        for model in models:
            if isinstance(model, dict):
                model = model.copy()
                model_type = model.pop("type")
                model = _m.BasePlotModel.construct(model_type, model)
            elif not isinstance(model, _m.BasePlotModel):
                raise ValueError(f"Must be a dict or BasePlotModel but got: {model!r}")
            out.append(model)
        return out

    def scatter(
        self,
        x: Sequence[float],
        y: Sequence[float],
        *,
        symbol: str = "o",
        size: float | None = None,
        **kwargs,
    ) -> _m.Scatter:
        """Add a scatter plot model to the axes."""
        model = _m.Scatter(
            x=x, y=y, symbol=symbol, size=size, **_m.parse_face_edge(kwargs)
        )
        self.models.append(model)
        return model

    def plot(self, x: Sequence[float], y: Sequence[float], **kwargs) -> _m.Line:
        """Add a line plot model to the axes."""
        model = _m.Line(x=x, y=y, **_m.parse_edge(kwargs))
        self.models.append(model)
        return model

    def bar(
        self,
        x: Sequence[float],
        y: Sequence[float],
        *,
        bottom: "float | Sequence[float] | NDArray[np.number]" = 0,
        bar_width: float | None = None,
        orient: Literal["vertical", "horizontal"] = "vertical",
        **kwargs,
    ) -> _m.Bar:
        """Add a bar plot model to the axes."""
        model = _m.Bar(
            x=x, y=y, bottom=bottom, bar_width=bar_width, orient=orient,
            **_m.parse_face_edge(kwargs),
        )  # fmt: skip
        self.models.append(model)
        return model

    def errorbar(
        self,
        x: Sequence[float],
        y: Sequence[float],
        *,
        x_error: "float | Sequence[float] | NDArray[np.number] | None" = None,
        y_error: "float | Sequence[float] | NDArray[np.number] | None" = None,
        capsize: float | None = None,
        **kwargs,
    ) -> _m.ErrorBar:
        """Add an error bar plot model to the axes."""
        model = _m.ErrorBar(
            x=x,
            y=y,
            x_error=x_error,
            y_error=y_error,
            capsize=capsize,
            **_m.parse_edge(kwargs),
        )
        self.models.append(model)
        return model

    def band(
        self,
        x: Sequence[float],
        y0: Sequence[float],
        y1: Sequence[float],
        *,
        orient: Literal["vertical", "horizontal"] = "vertical",
        **kwargs,
    ) -> _m.Band:
        """Add a band plot model to the axes."""
        model = _m.Band(x=x, y0=y0, y1=y1, orient=orient, **_m.parse_face_edge(kwargs))
        self.models.append(model)
        return model

    def hist(
        self,
        data: "Sequence[float] | NDArray[np.number]",
        *,
        bins: int = 10,
        range: tuple[float, float] | None = None,
        orient: Literal["vertical", "horizontal"] = "vertical",
        **kwargs,
    ) -> _m.Histogram:
        """Add a histogram plot model to the axes."""
        model = _m.Histogram(
            data=data, bins=bins, range=range, orient=orient,
            **_m.parse_face_edge(kwargs),
        )  # fmt: skip
        self.models.append(model)
        return model


class SingleAxes(BaseLayoutModel):
    axes: Axes = Field(default_factory=Axes, description="Child axes.")

    def merge_with(self, other: "SingleAxes") -> "SingleAxes":
        new_axes = self.axes.model_copy(
            update={"models": self.axes.models + other.axes.models}
        )
        return SingleAxes(axes=new_axes)


class Layout1D(BaseLayoutModel):
    """Layout model for 1D layout."""

    axes: list[Axes] = Field(default_factory=list, description="Child layouts.")
    share_x: bool = Field(False, description="Share x-axis or not.")
    share_y: bool = Field(False, description="Share y-axis or not.")

    def __getitem__(self, key: SupportsIndex) -> Axes:
        return self.axes[key]

    @classmethod
    def fill(cls, num: int) -> "Self":
        layout = cls()
        for _ in range(num):
            layout.axes.append(Axes())
        return layout

    def merge_with(self, other: "Self") -> "Self":
        if not isinstance(other, type(self)):
            raise ValueError(f"Cannot merge {type(self)} with {type(other)}")
        new_axes = [
            a.model_copy(update={"models": a.models + b.models})
            for a, b in zip(self.axes, other.axes)
        ]
        return type(self)(axes=new_axes, share_x=self.share_x, share_y=self.share_y)


class Row(Layout1D):
    """Layout model for row."""


class Column(Layout1D):
    """Layout model for column."""


class Grid(BaseLayoutModel):
    """Layout model for grid."""

    axes: list[list[Axes]] = Field(default_factory=list, description="Child layouts.")

    def __getitem__(self, key) -> Axes:
        return self.axes[key[0]][key[1]]

    @classmethod
    def fill(cls, rows: int, cols: int) -> "Self":
        layout = cls()
        for _ in range(rows):
            layout.axes.append([Axes() for _ in range(cols)])
        return layout

    def merge_with(self, other: "Self") -> "Self":
        if not isinstance(other, type(self)):
            raise ValueError(f"Cannot merge {type(self)} with {type(other)}")
        new_axes = [
            [
                a.model_copy(update={"models": a.models + b.models})
                for a, b in zip(row_a, row_b)
            ]
            for row_a, row_b in zip(self.axes, other.axes)
        ]
        return type(self)(axes=new_axes)
