from himena.plotting import layout


def figure():
    lo = layout.SingleAxes()
    return lo


def row(num: int = 1):
    lo = layout.Row.fill(num)
    return lo


def column(num: int = 1):
    lo = layout.Column.fill(num)
    return lo


def grid(rows: int = 1, cols: int = 1):
    lo = layout.Grid.fill(rows, cols)
    return lo
