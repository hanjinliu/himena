from typing import Literal, Sequence, TYPE_CHECKING, SupportsIndex

import numpy as np
from pydantic_compat import BaseModel, Field
from himena.standards.plotting import models as _m
from himena.standards.plotting.components import (
    Axis,
    AxesBase,
    parse_edge,
    parse_face_edge,
)
from himena.consts import PYDANTIC_CONFIG_STRICT, StandardType

if TYPE_CHECKING:
    from typing import Self
    from numpy.typing import NDArray


class BaseLayoutModel(BaseModel):
    model_config = PYDANTIC_CONFIG_STRICT

    hpad: float | None = Field(None, description="Horizontal padding.")
    vpad: float | None = Field(None, description="Vertical padding.")
    hspace: float | None = Field(None, description="Horizontal space.")
    vspace: float | None = Field(None, description="Vertical space.")
    background_color: str = Field("#FFFFFF", description="Background color.")

    def merge_with(self, other: "BaseLayoutModel") -> "BaseLayoutModel":
        raise NotImplementedError

    def model_dump_typed(self) -> dict:
        return {"type": type(self).__name__.lower(), **self.model_dump()}

    @classmethod
    def construct(self, model_type: str, dict_: dict) -> "BaseLayoutModel":
        from himena.standards.plotting.layout3d import SingleAxes3D

        if model_type == "singleaxes":
            return SingleAxes.model_validate(dict_)
        if model_type == "row":
            return Row.model_validate(dict_)
        if model_type == "column":
            return Column.model_validate(dict_)
        if model_type == "grid":
            return Grid.model_validate(dict_)
        if model_type == "singleaxes3d":
            return SingleAxes3D.model_validate(dict_)
        raise ValueError(f"Unknown layout model type: {model_type!r}")

    def show(self) -> None:
        """Show the layout in the current himena window."""
        from himena.widgets import current_instance

        ui = current_instance()
        ui.add_object(self, type=StandardType.PLOT, title="Plot")
        return None


class Axes(AxesBase):
    """Layout model for 2D axes."""

    x: Axis = Field(default_factory=Axis, description="X-axis settings.")
    y: Axis = Field(default_factory=Axis, description="Y-axis settings.")
    axis_color: str = Field("#000000", description="Axis color.")

    def scatter(
        self,
        x: Sequence[float],
        y: Sequence[float] | None = None,
        *,
        symbol: str = "o",
        size: float | None = None,
        **kwargs,
    ) -> _m.Scatter:
        """Add a scatter plot model to the axes."""
        x, y = _norm_xy(x, y)
        model = _m.Scatter(
            x=x, y=y, symbol=symbol, size=size, **parse_face_edge(kwargs)
        )
        self.models.append(model)
        return model

    def plot(
        self, x: Sequence[float], y: Sequence[float] | None = None, **kwargs
    ) -> _m.Line:
        """Add a line plot model to the axes."""
        x, y = _norm_xy(x, y)
        model = _m.Line(x=x, y=y, **parse_edge(kwargs))
        self.models.append(model)
        return model

    def bar(
        self,
        x: Sequence[float],
        y: Sequence[float] | None = None,
        *,
        bottom: "float | Sequence[float] | NDArray[np.number] | None" = None,
        bar_width: float | None = None,
        orient: Literal["vertical", "horizontal"] = "vertical",
        **kwargs,
    ) -> _m.Bar:
        """Add a bar plot model to the axes."""
        x, y = _norm_xy(x, y)
        if bottom is None:
            bottom = 0
        model = _m.Bar(
            x=x, y=y, bottom=bottom, bar_width=bar_width, orient=orient,
            **parse_face_edge(kwargs),
        )  # fmt: skip
        self.models.append(model)
        return model

    def errorbar(
        self,
        x: Sequence[float],
        y: Sequence[float] | None = None,
        *,
        x_error: "float | Sequence[float] | NDArray[np.number] | None" = None,
        y_error: "float | Sequence[float] | NDArray[np.number] | None" = None,
        capsize: float | None = None,
        **kwargs,
    ) -> _m.ErrorBar:
        """Add an error bar plot model to the axes."""
        x, y = _norm_xy(x, y)
        model = _m.ErrorBar(
            x=x,
            y=y,
            x_error=x_error,
            y_error=y_error,
            capsize=capsize,
            **parse_edge(kwargs),
        )
        self.models.append(model)
        return model

    def band(
        self,
        x: Sequence[float],
        y0: Sequence[float],
        y1: Sequence[float] | None = None,
        *,
        orient: Literal["vertical", "horizontal"] = "vertical",
        **kwargs,
    ) -> _m.Band:
        """Add a band plot model to the axes."""
        x = np.asarray(x)
        y0 = np.asarray(y0)
        if y1 is None:
            y1 = np.zeros_like(y0)
        model = _m.Band(x=x, y0=y0, y1=y1, orient=orient, **parse_face_edge(kwargs))
        self.models.append(model)
        return model

    def span(
        self,
        start: float,
        end: float,
        *,
        orient: Literal["vertical", "horizontal"] = "horizontal",
        **kwargs,
    ) -> _m.Span:
        """Add a span plot model to the axes."""
        model = _m.Span(start=start, end=end, orient=orient, **parse_face_edge(kwargs))
        self.models.append(model)
        return model

    def hist(
        self,
        data: "Sequence[float] | NDArray[np.number]",
        *,
        bins: int = 10,
        range: tuple[float, float] | None = None,
        orient: Literal["vertical", "horizontal"] = "vertical",
        stat: Literal["count", "density", "probability"] = "count",
        **kwargs,
    ) -> _m.Histogram:
        """Add a histogram plot model to the axes."""
        match stat:
            case "count":
                data = data
                density = False
            case "density":
                data = data
                density = True
            case "probability":
                data = data / len(data)
                density = False
            case _:
                raise ValueError(f"Unsupported histogram stat: {stat}")
        height, bins = np.histogram(data, bins=bins, range=range, density=density)
        model = _m.Histogram(
            height=height, bins=bins, orient=orient, **parse_face_edge(kwargs),
        )  # fmt: skip
        self.models.append(model)
        return model

    def text(
        self,
        x: Sequence[float],
        y: Sequence[float],
        text: Sequence[str],
        *,
        size: int = 12,
        color: str = "black",
        family: str = "Arial",
        anchor: _m.ANCHOR_STRINGS,
        rotation: float = 0,
    ) -> _m.Texts:
        """Add a text plot model to the axes."""
        model = _m.Texts(
            x=x, y=y, texts=text, size=size, color=color, family=family, anchor=anchor,
            rotation=rotation,
        )  # fmt: skip
        self.models.append(model)
        return model


class SingleAxes(BaseLayoutModel):
    axes: Axes = Field(default_factory=Axes, description="Child axes.")

    def merge_with(self, other: "SingleAxes") -> "SingleAxes":
        """Merge with another SingleAxes layout."""
        new_axes = self.axes.model_copy(
            update={"models": self.axes.models + other.axes.models}
        )
        return SingleAxes(axes=new_axes)

    ### Because there's only one axes, we can directly call the axes methods.
    def scatter(
        self,
        x: Sequence[float],
        y: Sequence[float] | None = None,
        *,
        symbol: str = "o",
        size: float | None = None,
        **kwargs,
    ) -> _m.Scatter:
        """Add a scatter plot model to the axes."""
        return self.axes.scatter(x=x, y=y, symbol=symbol, size=size, **kwargs)

    def plot(
        self,
        x: Sequence[float],
        y: Sequence[float] | None = None,
        **kwargs,
    ) -> _m.Line:
        """Add a line plot model to the axes."""
        return self.axes.plot(x=x, y=y, **kwargs)

    def bar(
        self,
        x: Sequence[float],
        y: Sequence[float] | None = None,
        *,
        bottom: "float | Sequence[float] | NDArray[np.number] | None" = None,
        bar_width: float | None = None,
        orient: Literal["vertical", "horizontal"] = "vertical",
        **kwargs,
    ) -> _m.Bar:
        """Add a bar plot model to the axes."""
        return self.axes.bar(
            x=x, y=y, bottom=bottom, bar_width=bar_width, orient=orient, **kwargs
        )

    def errorbar(
        self,
        x: Sequence[float],
        y: Sequence[float] | None = None,
        *,
        x_error: "float | Sequence[float] | NDArray[np.number] | None" = None,
        y_error: "float | Sequence[float] | NDArray[np.number] | None" = None,
        capsize: float | None = None,
        **kwargs,
    ) -> _m.ErrorBar:
        """Add an error bar plot model to the axes."""
        return self.axes.errorbar(
            x=x, y=y, x_error=x_error, y_error=y_error, capsize=capsize, **kwargs
        )

    def band(
        self,
        x: Sequence[float],
        y0: Sequence[float],
        y1: Sequence[float] | None = None,
        *,
        orient: Literal["vertical", "horizontal"] = "vertical",
        **kwargs,
    ) -> _m.Band:
        """Add a band plot model to the axes."""
        return self.axes.band(x=x, y0=y0, y1=y1, orient=orient, **kwargs)

    def hist(
        self,
        data: "Sequence[float] | NDArray[np.number]",
        *,
        bins: int = 10,
        range: tuple[float, float] | None = None,
        orient: Literal["vertical", "horizontal"] = "vertical",
        stat: Literal["count", "density", "probability"] = "count",
        **kwargs,
    ) -> _m.Histogram:
        """Add a histogram plot model to the axes."""
        return self.axes.hist(
            data=data, bins=bins, range=range, orient=orient, stat=stat, **kwargs
        )

    def text(
        self,
        x: Sequence[float],
        y: Sequence[float],
        text: Sequence[str],
        *,
        size: int = 12,
        color: str = "black",
        family: str = "Arial",
        rotation: float = 0,
        anchor: _m.ANCHOR_STRINGS = "center",
    ) -> _m.Texts:
        """Add a text plot model to the axes."""
        return self.axes.text(
            x=x, y=y, text=text, size=size, color=color, family=family, anchor=anchor,
            rotation=rotation,
        )  # fmt: skip


class SingleAxesStack(BaseLayoutModel):
    axes: dict[tuple[int, ...], Axes] = Field(
        default_factory=dict, description="Child axes."
    )


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


def _norm_xy(x, y) -> "tuple[NDArray[np.number], NDArray[np.number]]":
    if y is None:
        y = np.asarray(x)
        x = np.arange(len(y))
    else:
        x = np.asarray(x)
        y = np.asarray(y)
    if x.ndim != 1 or y.ndim != 1:
        raise ValueError(f"x and y must be 1D arrays, got {x.ndim}D and {y.ndim}D.")
    if x.shape != y.shape:
        raise ValueError(
            f"x and y must have the same shape, got {x.shape} and {y.shape}."
        )
    return x, y
