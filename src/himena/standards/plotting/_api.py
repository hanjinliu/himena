from himena.standards.plotting import layout


def figure() -> layout.SingleAxes:
    """Make a single axes layout model.

    Examples
    --------
    >>> from himena.standards import plotting as hplt
    >>> fig = hplt.figure()
    >>> fig.plot([0, 1, 2], [4, 2, 3], color="red")
    >>> fig.show()  # show as a sub-window in the current widget
    """
    lo = layout.SingleAxes()
    return lo


def row(num: int = 1) -> layout.Row:
    """Make a row layout model.

    Examples
    --------
    >>> from himena.standards import plotting as hplt
    >>> row = hplt.row(2)
    >>> row[0].plot([0, 1, 2], [4, 2, 3], color="red")
    >>> fig.show()  # show as a sub-window in the current widget
    """
    lo = layout.Row.fill(num)
    return lo


def column(num: int = 1) -> layout.Column:
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
    return lo


def grid(rows: int = 1, cols: int = 1) -> layout.Grid:
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
    return lo
