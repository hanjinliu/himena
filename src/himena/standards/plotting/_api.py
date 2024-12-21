from typing import Any
from himena.standards.plotting import layout, layout3d


def figure(background_color: Any = "white") -> layout.SingleAxes:
    """Make a single axes layout model.

    Examples
    --------
    >>> from himena.standards import plotting as hplt
    >>> fig = hplt.figure()
    >>> fig.plot([0, 1, 2], [4, 2, 3], color="red")
    >>> fig.show()  # show as a sub-window in the current widget
    """
    lo = layout.SingleAxes(background_color=background_color)
    return lo


def figure_3d(background_color: Any = "white") -> layout3d.SingleAxes3D:
    """Make a single 3D axes layout model.

    Examples
    --------
    >>> from himena.standards import plotting as hplt
    >>> fig = hplt.figure_3d()
    >>> fig.plot([0, 1, 2], [4, 2, 3], [6, 8, 7], color="red")
    >>> fig.show()  # show as a sub-window in the current widget
    """
    lo = layout3d.SingleAxes3D(background_color=background_color)
    return lo


def row(num: int = 1, *, background_color: Any = "white") -> layout.Row:
    """Make a row layout model.

    Examples
    --------
    >>> from himena.standards import plotting as hplt
    >>> row = hplt.row(2)
    >>> row[0].plot([0, 1, 2], [4, 2, 3], color="red")
    >>> fig.show()  # show as a sub-window in the current widget
    """
    lo = layout.Row.fill(num)
    lo.background_color = "white"
    return lo


def column(num: int = 1, *, background_color: Any = "white") -> layout.Column:
    """Make a column layout model.

    Parameters
    ----------
    num : int, optional
        Number of columns, by default 1

    Examples
    --------
    >>> from himena.standards import plotting as hplt
    >>> col = hplt.column(3)
    >>> col[0].plot([0, 1, 2], [4, 2, 3], color="blue")
    >>> col.show()  # show as a sub-window in the current widget
    """
    lo = layout.Column.fill(num)
    lo.background_color = "white"
    return lo


def grid(
    rows: int = 1, cols: int = 1, *, background_color: Any = "white"
) -> layout.Grid:
    """Make a grid layout model.

    Parameters
    ----------
    rows : int, optional
        Number of rows, by default 1
    cols : int, optional
        Number of columns, by default 1

    Examples
    --------
    >>> from himena.standards import plotting as hplt
    >>> grd = hplt.grid(2, 3)
    >>> grd[0, 0].plot([0, 1, 2], [4, 2, 3], color="green")
    >>> grd.show()  # show as a sub-window in the current widget
    """
    lo = layout.Grid.fill(rows, cols)
    lo.background_color = "white"
    return lo
