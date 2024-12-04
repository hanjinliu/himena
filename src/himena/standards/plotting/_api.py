from himena.standards.plotting import layout


def figure() -> layout.SingleAxes:
    """Make a single axes layout model."""
    lo = layout.SingleAxes()
    return lo


def row(num: int = 1) -> layout.Row:
    """Make a row layout model."""
    lo = layout.Row.fill(num)
    return lo


def column(num: int = 1) -> layout.Column:
    """Make a column layout model."""
    lo = layout.Column.fill(num)
    return lo


def grid(rows: int = 1, cols: int = 1) -> layout.Grid:
    """Make a grid layout model."""
    lo = layout.Grid.fill(rows, cols)
    return lo
