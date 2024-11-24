from himena.plotting import layout


def figure() -> layout.SingleAxes:
    lo = layout.SingleAxes()
    return lo


def row(num: int = 1) -> layout.Row:
    lo = layout.Row.fill(num)
    return lo


def column(num: int = 1) -> layout.Column:
    lo = layout.Column.fill(num)
    return lo


def grid(rows: int = 1, cols: int = 1) -> layout.Grid:
    lo = layout.Grid.fill(rows, cols)
    return lo
