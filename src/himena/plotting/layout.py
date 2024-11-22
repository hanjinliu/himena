from typing import Any, Literal, Sequence, TYPE_CHECKING

from pydantic_compat import BaseModel, Field
from himena.plotting import models
from himena.plotting.models import BasePlotModel

if TYPE_CHECKING:
    from typing import Self


class BaseLayoutModel(BaseModel):
    hpad: float | None = Field(None, description="Horizontal padding.")
    vpad: float | None = Field(None, description="Vertical padding.")
    hspace: float | None = Field(None, description="Horizontal space.")
    vspace: float | None = Field(None, description="Vertical space.")


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

    def scatter(self, x: Sequence[float], y: Sequence[float], **kwargs) -> None:
        self.models.append(models.Scatter(x=x, y=y, **kwargs))

    def plot(self, x: Sequence[float], y: Sequence[float], **kwargs) -> None:
        self.models.append(models.Line(x=x, y=y, **kwargs))

    def bar(self, x: Sequence[float], y: Sequence[float], **kwargs) -> None:
        self.models.append(models.Bar(x=x, y=y, **kwargs))

    def errorbar(self, x: Sequence[float], y: Sequence[float], **kwargs) -> None:
        self.models.append(models.ErrorBar(x=x, y=y, **kwargs))

    def hist(self, data: Sequence[float], **kwargs) -> None:
        self.models.append(models.Histogram(data=data, **kwargs))


class SingleAxes(BaseLayoutModel):
    axes: Axes = Field(default_factory=Axes, description="Child axes.")


class Layout1D(BaseLayoutModel):
    """Layout model for 1D layout."""

    axes: list[Axes] = Field(default_factory=list, description="Child layouts.")
    sharex: bool = Field(False, description="Share x-axis or not.")
    sharey: bool = Field(False, description="Share y-axis or not.")

    def __getitem__(self, key) -> Axes:
        return self.axes[key]

    @classmethod
    def fill(cls, num: int) -> "Self":
        layout = cls()
        for _ in range(num):
            layout.axes.append(Axes())
        return layout


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
