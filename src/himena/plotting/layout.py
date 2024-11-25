from typing import Any, Literal, Sequence, TYPE_CHECKING, SupportsIndex

from pydantic_compat import BaseModel, Field
from himena.plotting import models as _m
from himena.plotting.models import BasePlotModel

if TYPE_CHECKING:
    from typing import Self


class BaseLayoutModel(BaseModel):
    hpad: float | None = Field(None, description="Horizontal padding.")
    vpad: float | None = Field(None, description="Vertical padding.")
    hspace: float | None = Field(None, description="Horizontal space.")
    vspace: float | None = Field(None, description="Vertical space.")

    def merge_with(self, other: "BaseLayoutModel") -> "BaseLayoutModel":
        raise NotImplementedError


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

    models: list[BasePlotModel] = Field(
        default_factory=list, description="Child plot models."
    )
    title: str | StyledText | None = Field(None, description="Title of the axes.")
    x: Axis | None = Field(None, description="X-axis settings.")
    y: Axis | None = Field(None, description="Y-axis settings.")

    def scatter(
        self,
        x: Sequence[float],
        y: Sequence[float],
        **kwargs,
    ) -> _m.Scatter:
        """Add a scatter plot model to the axes."""
        model = _m.Scatter(x=x, y=y, **kwargs)
        self.models.append(model)
        return model

    def plot(self, x: Sequence[float], y: Sequence[float], **kwargs) -> _m.Line:
        """Add a line plot model to the axes."""
        model = _m.Line(x=x, y=y, **kwargs)
        self.models.append(model)
        return model

    def bar(self, x: Sequence[float], y: Sequence[float], **kwargs) -> _m.Bar:
        """Add a bar plot model to the axes."""
        model = _m.Bar(x=x, y=y, **kwargs)
        self.models.append(model)
        return model

    def errorbar(self, x: Sequence[float], y: Sequence[float], **kwargs) -> _m.ErrorBar:
        """Add an error bar plot model to the axes."""
        model = _m.ErrorBar(x=x, y=y, **kwargs)
        self.models.append(model)
        return model

    def hist(self, data: Sequence[float], **kwargs) -> _m.Histogram:
        """Add a histogram plot model to the axes."""
        model = _m.Histogram(data=data, **kwargs)
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
